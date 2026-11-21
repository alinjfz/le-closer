"""Live assistance checks; no network requests or running server required."""
import asyncio
import base64
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi import HTTPException
from app import main, live_assistant as live, mistral_media
from app.models import Task
from app.segments import make_segment
from app.state import CallStore


class AssistantTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = CallStore()
        self.state = self.store.create_call()

    async def asyncTearDown(self):
        await self.store.stop_jobs(self.state.call_id)

    async def test_notes_preserve_personal_notes_and_check_only_returned_ids(self):
        state = self.state
        state.personal_notes = 'Do not forget the pilot.'
        state.tasks = [Task(id='sent', title='Send specification', owner='rep', origin='promise', status='queued'),
                       Task(id='planned', title='Arrange pilot', owner='rep', origin='promise', status='queued')]
        with patch.object(live, 'has_api_key', return_value=True), patch.object(live, 'chat_json', new_callable=AsyncMock,
                return_value={'markdown': '# Notes\nSpecification sent.', 'completed_task_ids': ['sent', 'nonexistent']}) as chat:
            await live.update_notes(state, self.store, 'REP: I sent the specification, will arrange the pilot.')
        self.assertEqual(state.tasks[0].status, 'done')
        self.assertEqual(state.tasks[1].status, 'queued')
        self.assertEqual(state.personal_notes, 'Do not forget the pilot.')
        self.assertIn(state.personal_notes, chat.call_args.args[2])
        self.assertTrue(state.notes['live'])

    async def test_followups_dedupe_and_resolve_to_reviewable_answer(self):
        seg = make_segment(self.state, 'client', 'Can we start a pilot?')
        with patch.object(live, 'has_api_key', return_value=True), patch.object(live, 'chat_json', new_callable=AsyncMock) as chat:
            chat.return_value = {'questions': [{'title': 'Pilot timing', 'question': 'When should the pilot begin?'}]}
            await live.resolve_loose_ends(self.state, self.store, seg, seg.text)
            await live.resolve_loose_ends(self.state, self.store, seg, seg.text)
            self.assertEqual(len(self.state.tasks), 1)
            task = self.state.tasks[0]
            chat.return_value = {'answers': [{'task_id': task.id, 'answer': 'The client confirmed Monday.'}]}
            await live.resolve_loose_ends(self.state, self.store, seg, 'CLIENT: The pilot should start Monday.')
        self.assertEqual(task.status, 'ready')
        self.assertTrue(task.result_ref)
        self.assertIn('Monday', self.state.cards[-1].body)

    async def test_translation_preserves_original_and_ignores_stale_target(self):
        state = self.state
        state.settings.translation_language = 'en'
        seg = make_segment(state, 'client', 'Ça marche.')
        with patch.object(live, 'has_api_key', return_value=True), patch.object(live, 'chat_json', new_callable=AsyncMock,
                return_value={'translation': 'That works.', 'source_language': 'fr', 'cultural_note': 'Agreement in context.'}):
            await live.translate_segment(state, self.store, seg)
        self.assertEqual(seg.text, 'Ça marche.')
        self.assertEqual(seg.translation, 'That works.')
        async def stale(*args):
            state.settings.translation_language = 'de'
            return {'translation': 'Wrong target'}
        with patch.object(live, 'has_api_key', return_value=True), patch.object(live, 'chat_json', stale):
            await live.translate_segment(state, self.store, seg)
        self.assertEqual(seg.translation, 'That works.')

    async def test_specialists_concurrent_and_queued_updates_coalesced(self):
        seg = make_segment(self.state, 'client', 'A new question?')
        entered = set()
        ready = asyncio.Event()
        async def job(name):
            entered.add(name)
            if len(entered) == 2:
                ready.set()
            await asyncio.wait_for(ready.wait(), 1)
        async def notes_job(*args):
            await job('notes')
        async def followup_job(*args):
            await job('followup')
        with patch.object(live, 'update_notes', side_effect=notes_job) as notes, \
             patch.object(live, 'resolve_loose_ends', side_effect=followup_job):
            await live.process_segment(self.state, self.store, seg)
            await live.process_segment(self.state, self.store, seg)
        self.assertEqual(entered, {'notes', 'followup'})
        self.assertEqual(notes.call_count, 1)

    async def test_wake_word_answers(self):
        with patch.object(live, 'has_api_key', return_value=False), patch.object(live, 'chat_text', new_callable=AsyncMock, return_value='A Monday pilot.'):
            for speaker in ('rep', 'client'):
                seg = make_segment(self.state, speaker, 'Copilot, can you answer what we agreed?')
                await live.process_segment(self.state, self.store, seg)
        self.assertEqual(len(self.state.assistant_answers), 2)
        self.assertEqual(self.state.assistant_answers[-1]['text'], 'A Monday pilot.')

    async def test_prototype_generated_and_generation_failure_visible(self):
        with patch.object(live, 'has_api_key', return_value=True), patch.object(live, 'chat_text', new_callable=AsyncMock,
                return_value='```html\n<html><body>Shipment dashboard</body></html>\n```'):
            await live.generate_prototype(self.state, self.store, 'Shipment dashboard', 'code')
        proto = self.state.prototypes[0]
        self.assertIn('Shipment dashboard', proto['html'])
        self.assertIn('connect-src', proto['html'])
        self.assertNotIn('```', proto['html'])
        self.assertEqual(self.state.tasks[0].status, 'ready')
        with patch.object(mistral_media, 'generate_image', new_callable=AsyncMock, side_effect=ValueError('No image access')):
            await live.generate_prototype(self.state, self.store, 'Physical scanner', 'image')
        self.assertEqual(len(self.state.prototypes), 1)
        self.assertEqual(self.state.tasks[-1].status, 'queued')
        self.assertEqual(self.state.activity[-1].status, 'error')

    async def test_stop_jobs_releases_call_resources(self):
        stopped = asyncio.Event()
        async def work():
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()
        task = self.store.spawn(self.state.call_id, work())
        await asyncio.sleep(0)
        await self.store.stop_jobs(self.state.call_id)
        self.assertTrue(task.cancelled())
        self.assertTrue(stopped.is_set())
        self.assertNotIn(self.state.call_id, self.store.jobs)

    async def test_speech_gate_and_ended_call(self):
        self.state.settings.tts_enabled = False
        with patch.object(main, 'store', self.store):
            with self.assertRaises(HTTPException) as error:
                await main.assistant_speech(self.state.call_id, 'answer')
            self.assertEqual(error.exception.status_code, 409)
            self.state.ended = True
            with self.assertRaises(HTTPException):
                await main.assistant_ask(self.state.call_id, main.QuestionRequest(question='hello'))

    async def test_notes_continue_when_router_fails(self):
        from app.router import run_segment
        seg = make_segment(self.state, 'client', 'The pilot is on Monday.')
        with patch('app.router.route_segment', new_callable=AsyncMock, side_effect=RuntimeError('router unavailable')), \
             patch.object(live, 'has_api_key', return_value=False):
            await run_segment(self.state, self.store, seg)
        self.assertIn('Monday', self.state.notes['markdown'])
        self.assertTrue(any(a.agent == 'Router' and a.status == 'error' for a in self.state.activity))

    async def test_api_flow_and_validation(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
            state = self.state
            with patch.object(main, 'store', self.store), patch.object(live, 'chat_text', new_callable=AsyncMock, return_value='Pilot starts Monday.'):
                result = await client.post(f'/calls/{state.call_id}/assistant/ask', json={'question': 'What was agreed?'})
                self.assertEqual(result.status_code, 200)
                await asyncio.gather(*list(self.store.jobs[state.call_id]))
                self.assertEqual(state.assistant_answers[-1]['text'], 'Pilot starts Monday.')
                invalid = await client.post(f'/calls/{state.call_id}/prototype', json={'topic': '', 'kind': 'video'})
                self.assertEqual(invalid.status_code, 422)
                await client.post(f'/calls/{state.call_id}/notes/personal', json={'text': 'Check pilot owner'})
                self.assertEqual(state.personal_notes, 'Check pilot owner')
                state.settings.tts_enabled = True
                with patch.object(mistral_media, 'generate_speech', new_callable=AsyncMock, return_value=b'mp3'):
                    speech = await client.get(f'/calls/{state.call_id}/assistant/speech/{state.assistant_answers[-1]["id"]}')
                self.assertEqual(speech.content, b'mp3')
                with patch.object(main.post_call, 'run_post_call', new_callable=AsyncMock):
                    await client.post(f'/calls/{state.call_id}/end')
                    await asyncio.gather(*list(self.store.jobs[state.call_id]))
                closed = await client.post(f'/calls/{state.call_id}/assistant/ask', json={'question': 'Anything else?'})
                self.assertEqual(closed.status_code, 409)

    async def test_language_and_mute_settings_are_independent(self):
        from app.models import AssistantSettings
        self.assertTrue(self.state.settings.tts_enabled)
        with patch.object(main, 'store', self.store), patch('app.mistral_client.has_api_key', return_value=True):
            await main.assistant_settings(self.state.call_id, AssistantSettings(translation_language='fr'))
            self.assertTrue(self.state.settings.tts_enabled)
            await main.assistant_settings(self.state.call_id, AssistantSettings(tts_enabled=False))
            self.assertFalse(self.state.settings.tts_enabled)
            self.assertEqual(self.state.settings.translation_language, 'fr')
            await main.assistant_settings(self.state.call_id, AssistantSettings(translation_language='de'))
            self.assertFalse(self.state.settings.tts_enabled)
            self.assertEqual(self.state.settings.translation_language, 'de')

    async def test_media_http_contracts(self):
        requests = []
        png = b'\x89PNG\r\n\x1a\nexample'
        def handle(request):
            requests.append(request)
            if request.url.path.endswith('/audio/speech'):
                return httpx.Response(200, json={'audio_data': base64.b64encode(b'audio').decode()})
            if request.url.path.endswith('/conversations'):
                return httpx.Response(200, json={'outputs': [{'content': [{'type': 'tool_file', 'tool': 'image_generation', 'file_id': 'file123'}]}]})
            return httpx.Response(200, content=png, headers={'content-type': 'application/octet-stream'})
        real_client = httpx.AsyncClient
        def client(**kwargs):
            return real_client(transport=httpx.MockTransport(handle), **kwargs)
        with patch.object(mistral_media.config, 'MISTRAL_API_KEY', 'test'), patch.object(mistral_media.httpx, 'AsyncClient', side_effect=client):
            self.assertEqual(await mistral_media.generate_speech('Hello'), b'audio')
            self.assertTrue((await mistral_media.generate_image('A scanner')).startswith('data:image/png;base64,'))
        self.assertEqual(len(requests), 3)
        self.assertTrue(all(r.url.host == 'api.mistral.ai' for r in requests))


if __name__ == '__main__':
    unittest.main()
