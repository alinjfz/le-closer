"""Chosen merge behavior. Provider calls are mocked; the demo replay runs offline."""
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from app import calculator, config, main, mistral_client
from app.models import Card, DealFacts
from app.state import CallStore
from app.segments import make_segment
from app.fast_agents import cultural_cue, prototype, reference, numbers_extractor, mindmap
from app.workflows import post_call


class MergeChoiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = CallStore()
        self.live = self.store.create_call(client={'country': 'FR'})
        self.demo = self.store.create_call(demo=True)

    async def asyncTearDown(self):
        for call_id in list(self.store.jobs):
            await self.store.stop_jobs(call_id)

    async def test_live_culture_is_general_and_uses_glossary(self):
        seg = make_segment(self.live, 'client', 'We need the Lenkungsausschuss to approve this.')
        with patch.object(cultural_cue, 'chat_text', new_callable=AsyncMock, return_value='A steering committee must review the proposal.') as chat:
            await cultural_cue.run(self.live, self.store, seg, {})
        self.assertEqual(chat.call_args.args[1], cultural_cue.LIVE_SYSTEM)
        self.assertIn('never infer personality', chat.call_args.args[1])
        self.assertIn('steering committee', chat.call_args.args[2])
        self.assertEqual(self.live.cards[-1].kind, 'cultural')

    async def test_demo_culture_uses_incoming_persona_and_phrase(self):
        with patch.object(cultural_cue, 'chat_text', new_callable=AsyncMock, return_value='Formal demo explanation.') as chat:
            seg = make_segment(self.demo, 'client', 'Please clarify the hosting.')
            await cultural_cue.run(self.demo, self.store, seg, {})
            self.assertEqual(chat.call_args.args[1], cultural_cue.DEMO_SYSTEM)
            self.assertIn('NordWerk', chat.call_args.args[1])
            seg = make_segment(self.demo, 'client', 'The Lenkungsausschuss needs to approve.')
            await cultural_cue.run(self.demo, self.store, seg, {})
            self.assertEqual(chat.await_count, 1)
        self.assertIn('steering committee', self.demo.cards[-1].body)

    async def test_live_workflow_requests_use_only_mistral_pipeline(self):
        seg = make_segment(self.live, 'rep', 'Draw our architecture.')
        with patch('app.live_assistant.generate_prototype', new_callable=AsyncMock) as generate:
            await prototype.run(self.live, self.store, seg, {})
        generate.assert_awaited_once_with(self.live, self.store, 'Generated workflow diagram from the call', 'code')
        self.assertEqual(self.live.prototypes, [])

    async def test_demo_can_produce_both_workflows_without_duplicates(self):
        make_segment(self.demo, 'client', 'Our sensors use MQTT through a gateway to SAP.')
        seg = make_segment(self.demo, 'rep', 'We have the workflow diagram ready.')
        async def generated(state, store, topic, kind):
            state.prototypes.append({'id': 'generated', 'title': topic, 'kind': kind, 'html': '<h1>Generated</h1>'})
        with patch('app.mistral_client.has_api_key', return_value=True), patch('app.live_assistant.generate_prototype', side_effect=generated) as generate:
            await prototype.run(self.demo, self.store, seg, {})
            await prototype.run(self.demo, self.store, seg, {})
        self.assertEqual(len(self.demo.prototypes), 2)
        self.assertIn('Workflow diagram:', self.demo.prototypes[0]['title'])
        self.assertIn('SAP', self.demo.prototypes[0]['html'])
        self.assertEqual(generate.await_count, 1)

    async def test_offline_demo_keeps_template_available(self):
        seg = make_segment(self.demo, 'rep', 'Draw this workflow.')
        with patch('app.mistral_client.has_api_key', return_value=False), patch('app.live_assistant.generate_prototype', new_callable=AsyncMock) as generate:
            await prototype.run(self.demo, self.store, seg, {})
        self.assertEqual(len(self.demo.prototypes), 1)
        generate.assert_not_awaited()

    async def test_references_preserve_active_and_pinned_cards_in_both_modes(self):
        for state in (self.live, self.demo):
            state.cards = [Card(id='quote', kind='deal', title='Quote', body='Price', status='active'),
                           Card(id='research', kind='research', title='Research', body='Evidence', status='pinned')]
            seg = make_segment(state, 'rep', 'I mentioned the quote and whitepaper.')
            await reference.run(state, self.store, seg, {})
            self.assertEqual([card.status for card in state.cards], ['active', 'pinned'])
            self.assertTrue(all(card.meta['referenced_on_call'] for card in state.cards))

    async def test_annual_and_total_quotes_and_volume_boundaries(self):
        pricing = calculator._load_pricing()
        for count, rate in ((499, 3.0), (500, 2.4), (1999, 2.4), (2000, 1.8)):
            one = calculator.scale_quote(count, 1, pricing)
            two = calculator.scale_quote(count, 2, pricing)
            self.assertEqual(two['annual'], count * rate * 12)
            self.assertEqual(two['annual'], one['annual'])
            self.assertEqual(two['contract_total'], 2 * two['annual'])
        number = calculator.compute_numbers(DealFacts(sensors=1200, seats=40, contract_years=2))
        self.assertEqual(number.quote_annual, 34560)
        self.assertEqual(number.quote_contract_total, 69120)
        self.assertEqual(number.deal_value, 69120)
        self.assertEqual(number.price_at_requested_discount, 34560)
        self.assertIsNone(number.margin_pct)
        self.assertEqual(calculator.tier_comparison(1200, 2, pricing)[0]['annual'], 25920)

    async def test_sensor_scale_is_not_overwritten_by_rep_hypotheticals(self):
        numbers_extractor._extract(self.live, '1,200 sensors across 3 plants and 40 operators, 2-year contract.', 'client')
        numbers_extractor._extract(self.live, 'If you scale past 2,000 sensors...', 'rep')
        self.assertEqual(self.live.facts.sensors, 1200)
        self.assertEqual(self.live.facts.plants, 3)
        self.assertEqual(self.live.facts.contract_years, 2)

    async def test_live_offline_mindmap_does_not_invent_iot_scenario(self):
        seg = make_segment(self.live, 'client', 'We operate a bakery.')
        with patch.object(mindmap, 'chat_text', new_callable=AsyncMock, return_value=''), patch('app.mistral_client.has_api_key', return_value=False):
            await mindmap.run(self.live, self.store, seg, {})
        self.assertIn('bakery', self.live.mindmap_md)
        self.assertNotIn('MQTT', self.live.mindmap_md)

    async def test_entire_demo_replays_with_correct_quotes_and_original_ui_events(self):
        script = json.loads((Path(__file__).parent / 'demo/script.json').read_text(encoding='utf-8'))
        self.demo.demo_status = 'playing'
        with patch.object(main, 'store', self.store), patch.object(config, 'MISTRAL_API_KEY', ''), patch.object(mistral_client, '_client', None):
            await main._play_script(self.demo, script, 0)
            await post_call.run_post_call(self.demo, self.store)
        self.assertEqual(len(self.demo.segments), len(script))
        self.assertEqual(self.demo.demo_status, 'finished')
        self.assertEqual(self.demo.facts.sensors, 1200)
        self.assertEqual(self.demo.numbers.quote_annual, 34560)
        self.assertEqual(self.demo.numbers.quote_contract_total, 69120)
        self.assertTrue(self.demo.prototypes)
        self.assertTrue(any(c.kind == 'cultural' and 'steering committee' in c.body for c in self.demo.cards))
        self.assertTrue(any(c.kind == 'deal' and '34,560' in c.body and c.status == 'active' for c in self.demo.cards))
        self.assertIn('34,560', self.demo.notes['markdown'])
        self.assertIn('69,120 total', self.demo.followup_draft)
        self.assertNotIn('69,120/year', self.demo.followup_draft)
        self.assertTrue(all(c.status != 'dismissed' for c in self.demo.cards))


if __name__ == '__main__':
    unittest.main()
