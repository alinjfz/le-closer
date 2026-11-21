"""Addressed research requests, real-time dates, citations and nonblocking dispatch."""
import asyncio
from datetime import datetime
import json
import unittest
from unittest.mock import AsyncMock, patch
import httpx

from app import config, live_assistant as live, research_client
from app.segments import make_segment
from app.state import CallStore


class ResearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = CallStore()
        self.state = self.store.create_call()

    async def asyncTearDown(self):
        await self.store.stop_jobs(self.state.call_id)

    async def test_wake_word_recognizes_hyphenated_spaced_and_unicode_forms(self):
        for name in ('copilot', 'co-pilot', 'co pilot', 'CO–PILOT', 'co‑pilot', 'Le Closer'):
            seg = make_segment(self.state, 'rep', f'Oh, {name}, can you find the weather for tomorrow in France?')
            self.assertEqual(live.invoked_question(self.state, self.store, seg), seg.text)
        seg = make_segment(self.state, 'rep', 'We went co-piloting yesterday.')
        self.assertIsNone(live.invoked_question(self.state, self.store, seg))

    async def test_wake_word_split_over_segments(self):
        first = make_segment(self.state, 'rep', 'Oh, co-pilot,')
        self.assertIsNone(live.invoked_question(self.state, self.store, first))
        other = make_segment(self.state, 'client', 'I have a pricing question.')
        self.assertIsNone(live.invoked_question(self.state, self.store, other))
        question = make_segment(self.state, 'rep', 'Can you find the weather for tomorrow in France?')
        self.assertIn('weather', live.invoked_question(self.state, self.store, question))
        self.assertEqual(self.store.pending_invocations, {})

    async def test_request_routing_preserves_meeting_questions(self):
        self.assertTrue(live.wants_research(self.state, 'Co-pilot, find the weather tomorrow in France.'))
        self.assertTrue(live.wants_research(self.state, 'Copilot, research SAP documentation.'))
        self.assertFalse(live.wants_research(self.state, 'Copilot, find what we agreed in our call.'))
        self.state.assistant_answers = [{'mode': 'research', 'text': 'Which city or region in France?'}]
        self.assertTrue(live.wants_research(self.state, 'Co-pilot, Paris.'))
        self.assertFalse(live.wants_research(self.state, 'Copilot, what did we decide?'))

    async def test_invoked_research_starts_before_notes_finish(self):
        seg = make_segment(self.state, 'rep', 'Oh, co-pilot, can you find the weather for tomorrow in France?')
        notes_started, release_notes, researched = asyncio.Event(), asyncio.Event(), asyncio.Event()
        async def notes(*args):
            notes_started.set()
            await release_notes.wait()
        async def research(*args):
            researched.set()
            return {'text': 'Which city or region in France?', 'sources': [], 'searched': False}
        with patch.object(live, 'update_notes', side_effect=notes), patch.object(live, 'resolve_loose_ends', new_callable=AsyncMock), patch.object(research_client, 'research_question', side_effect=research):
            job = self.store.spawn(self.state.call_id, live.process_segment(self.state, self.store, seg))
            try:
                await asyncio.wait_for(notes_started.wait(), 1)
                await asyncio.wait_for(researched.wait(), 1)
                self.assertEqual(self.state.assistant_answers[-1]['text'], 'Which city or region in France?')
                self.assertEqual(self.state.assistant_answers[-1]['mode'], 'research')
                self.assertFalse(job.done())
            finally:
                release_notes.set()
                await job

    async def test_research_failure_does_not_fabricate_weather(self):
        with patch.object(research_client, 'research_question', new_callable=AsyncMock, side_effect=RuntimeError('unavailable')), patch.object(live, 'chat_text', new_callable=AsyncMock) as chat:
            answer = await live.answer_question(self.state, self.store, 'Copilot, weather tomorrow in Paris?')
        chat.assert_not_awaited()
        self.assertIn('couldn’t complete', answer['text'])
        self.assertEqual(answer['sources'], [])
        self.assertFalse(answer['searched'])

    async def test_research_api_contract_dates_sources_and_thinking_filter(self):
        captured = []
        def handle(request):
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={'outputs': [
                {'type': 'tool.execution', 'name': 'web_search'},
                {'type': 'message.output', 'content': [
                    {'type': 'thinking', 'thinking': [{'type': 'text', 'text': 'PRIVATE'}]},
                    {'type': 'text', 'text': 'Forecast for Paris on 2026-11-22.'},
                    {'type': 'tool_reference', 'tool': 'web_search', 'title': 'Forecast source', 'url': 'https://example.com/forecast'},
                    {'type': 'tool_reference', 'tool': 'web_search', 'title': 'Duplicate', 'url': 'https://example.com/forecast'},
                    {'type': 'tool_reference', 'tool': 'web_search', 'title': 'Unsafe', 'url': 'javascript:alert(1)'},
                ]},
            ]})
        real_client = httpx.AsyncClient
        history = [{'mode': 'meeting', 'question': 'PRIVATE MEETING', 'text': 'Confidential budget'},
                   {'mode': 'research', 'question': 'France weather?', 'text': 'Which city?'}]
        with patch.object(config, 'MISTRAL_API_KEY', 'test'), patch.object(research_client, 'research_timestamp', return_value='2026-11-21T12:00:00+00:00'), patch.object(research_client.httpx, 'AsyncClient', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw)):
            result = await research_client.research_question('Paris tomorrow', history)
        self.assertNotIn('PRIVATE', result['text'])
        self.assertEqual(len(result['sources']), 1)
        self.assertTrue(result['searched'])
        self.assertIn('2026-11-21T12:00:00', captured[0]['instructions'])
        self.assertIn('ask which city or region', captured[0]['instructions'])
        self.assertEqual(captured[0]['tools'], [{'type': 'web_search'}])
        self.assertFalse(captured[0]['store'])
        self.assertNotIn('Confidential', captured[0]['inputs'])
        self.assertIn('Which city?', captured[0]['inputs'])

    async def test_modern_plain_text_answer_uses_tool_result_sources(self):
        def handle(request):
            return httpx.Response(200, json={'outputs': [
                {'type': 'tool.execution', 'name': 'web_search', 'info': {'result': json.dumps({'results': [
                    {'url': 'https://example.com/weather', 'title': 'Weather source'},
                ]})}},
                {'type': 'message.output', 'content': 'Verified forecast.'},
            ]})
        real_client = httpx.AsyncClient
        with patch.object(config, 'MISTRAL_API_KEY', 'test'), patch.object(research_client.httpx, 'AsyncClient', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw)):
            result = await research_client.research_question('Paris tomorrow')
        self.assertEqual(result['sources'], [{'title': 'Weather source', 'url': 'https://example.com/weather'}])
        self.assertEqual(result['text'], 'Verified forecast.')

    async def test_plain_markdown_tool_results_preserve_source_links(self):
        def handle(request):
            return httpx.Response(200, json={'outputs': [
                {'type': 'tool.execution', 'name': 'web_search', 'info': {'result': 'Forecast source: https://example.com/weather.'}},
                {'type': 'message.output', 'content': 'The forecast is available.'},
            ]})
        real_client = httpx.AsyncClient
        with patch.object(config, 'MISTRAL_API_KEY', 'test'), patch.object(research_client.httpx, 'AsyncClient', side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw)):
            result = await research_client.research_question('Paris tomorrow')
        self.assertEqual(result['sources'][0]['url'], 'https://example.com/weather')

    async def test_research_without_api_key_fails_explicitly(self):
        with patch.object(config, 'MISTRAL_API_KEY', ''):
            with self.assertRaisesRegex(ValueError, 'API key'):
                await research_client.research_question('Weather tomorrow?')

    async def test_research_timestamp_has_timezone(self):
        timestamp = datetime.fromisoformat(research_client.research_timestamp())
        self.assertIsNotNone(timestamp.tzinfo)


if __name__ == '__main__':
    unittest.main()
