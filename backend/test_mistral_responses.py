"""Provider response regressions: final text, modern images, call-based generation."""
import asyncio
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
import httpx
from fastapi import HTTPException
from app import main, mistral_client, mistral_media
from app.segments import make_segment
from app.state import CallStore


class ResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_filters_thinking_chunks_and_preserves_markdown(self):
        content = [SimpleNamespace(type='thinking', thinking=[{'type': 'text', 'text': 'PRIVATE REASONING'}]),
                   SimpleNamespace(type='text', text='**Final answer**\n\n- Supported with verification.')]
        complete = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))]))
        client = SimpleNamespace(chat=SimpleNamespace(complete=complete))
        with patch.object(mistral_client, 'get_client', return_value=client):
            text = await mistral_client.chat_text('test', 'system', 'user')
        self.assertEqual(text, '**Final answer**\n\n- Supported with verification.')
        self.assertNotIn('PRIVATE', text)
        self.assertNotIn('Chunk', text)

    async def test_json_uses_only_final_text(self):
        content = [{'type': 'thinking', 'thinking': [{'type': 'text', 'text': 'hidden'}]},
                   {'type': 'text', 'text': '{"labels": []}'}]
        client = SimpleNamespace(chat=SimpleNamespace(complete=Mock(return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]))))
        with patch.object(mistral_client, 'get_client', return_value=client):
            result = await mistral_client.chat_json('test', 'system', 'user')
        self.assertEqual(result, {'labels': []})
        self.assertEqual(mistral_client.response_text('plain text'), 'plain text')
        self.assertEqual(mistral_client.response_text(None), '')

    async def test_modern_image_tool_result_url(self):
        requests = []
        url = 'https://images.example.com/generated.png?signature=example'
        def handle(request):
            requests.append(request)
            return httpx.Response(200, json={'outputs': [
                {'type': 'tool.execution', 'name': 'image_generation', 'info': {'result': json.dumps({'url': url})}},
                {'type': 'message.output', 'content': [{'type': 'text', 'text': 'Here is your image.'}]}]})
        real_client = httpx.AsyncClient
        with patch.object(mistral_media.config, 'MISTRAL_API_KEY', 'test'), patch.object(mistral_media.httpx, 'AsyncClient',
                side_effect=lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw)):
            result = await mistral_media.generate_image('Draw the product')
        self.assertEqual(result, url)
        # Signed image URLs are rendered directly, not fetched with our API key.
        self.assertEqual(len(requests), 1)
        self.assertIn('image_generation', json.loads(requests[0].content)['instructions'])

    async def test_no_image_response_still_reports_failure(self):
        real_client = httpx.AsyncClient
        with patch.object(mistral_media.config, 'MISTRAL_API_KEY', 'test'), patch.object(mistral_media.httpx, 'AsyncClient',
                side_effect=lambda **kw: real_client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={'outputs': []})), **kw)):
            with self.assertRaisesRegex(ValueError, 'returned no image'):
                await mistral_media.generate_image('Draw the product')

    async def test_call_based_image_requires_context_and_passes_notes(self):
        store = CallStore()
        state = store.create_call()
        try:
            with patch.object(main, 'store', store):
                with self.assertRaises(HTTPException):
                    await main.prototype(state.call_id, main.PrototypeRequest(kind='image', based_on_call=True))
                make_segment(state, 'client', 'We need a warehouse dashboard.')
                state.notes = {'markdown': 'Amber status indicators'}
                state.personal_notes = 'Mobile first'
                with patch.object(mistral_media, 'generate_image', new_callable=AsyncMock, return_value='data:image/png;base64,example') as image:
                    await main.prototype(state.call_id, main.PrototypeRequest(kind='image', based_on_call=True))
                    await asyncio.gather(*list(store.jobs[state.call_id]))
                prompt = image.call_args.args[0]
                self.assertIn('warehouse dashboard', prompt)
                self.assertIn('Amber status indicators', prompt)
                self.assertIn('Mobile first', prompt)
                self.assertEqual(state.prototypes[-1]['kind'], 'image')
        finally:
            await store.stop_jobs(state.call_id)

    async def test_start_button_cannot_launch_duplicate_demo_scripts(self):
        store = CallStore()
        state = store.create_call(demo=True)
        async def play(*args):
            await asyncio.Event().wait()
        try:
            with patch.object(main, 'store', store), patch.object(main, '_play_script', side_effect=play):
                await main.demo_play(state.call_id)
                again = await main.demo_play(state.call_id)
                self.assertEqual(again['status'], 'playing')
                self.assertEqual(len(store.jobs[state.call_id]), 1)
        finally:
            await store.stop_jobs(state.call_id)


if __name__ == '__main__':
    unittest.main()
