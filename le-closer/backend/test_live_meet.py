"""Live Meet regression checks: python3 -m unittest test_live_meet -v."""
import asyncio
import base64
import json
import unittest
from unittest.mock import AsyncMock, patch
from app import main
from app.audio_gateway import VoxtralSession
from app.state import CallStore


class LiveMeetTests(unittest.IsolatedAsyncioTestCase):
    async def test_reject_invalid_live_launch(self):
        for body in ({"start_bot": True, "demo": True},
                     {"start_bot": True},
                     {"start_bot": True, "recording_consent": True, "meet_url": "https://example.com/abc"}):
            self.assertIn("error", await main.create_call(body))

    async def test_launch_once_and_cleanup_at_end(self):
        entered, stopped = asyncio.Event(), asyncio.Event()
        async def bot(*args, **kwargs):
            self.assertTrue(kwargs["consent"])
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()
        body = {"start_bot": True, "recording_consent": True,
                "meet_url": "https://meet.google.com/abc-defg-hij"}
        with patch("bot.meet_bot.run_bot", bot), \
             patch("app.mistral_client.has_api_key", return_value=True), \
             patch("app.workflows.research.research_brief", new_callable=AsyncMock), \
             patch.object(main.post_call, "cultural_briefing", new_callable=AsyncMock), \
             patch.object(main.post_call, "run_post_call", new_callable=AsyncMock):
            result = await main.create_call(body)
            cid = result["call_id"]
            try:
                await asyncio.wait_for(entered.wait(), 1)
                self.assertIn("already running", (await main.create_call(body))["error"])
                await main.end_call(cid)
                self.assertTrue(stopped.is_set())
                self.assertNotIn(cid, main.bot_tasks)
            finally:
                await main.stop_bot(cid)

    async def test_audio_forwarding_and_late_words(self):
        store = CallStore()
        state = store.create_call()
        session = VoxtralSession(state, store, "client")
        session._client = AsyncMock()
        await session.send_audio(b"\x01\x00\x02\x00")
        payload = json.loads(session._client.send.call_args.args[0])
        self.assertEqual(payload["type"], "input_audio.append")
        self.assertEqual(base64.b64decode(payload["audio"]), b"\x01\x00\x02\x00")
        with patch("app.router.route_segment", new_callable=AsyncMock, return_value={"labels": []}), \
             patch("app.router.dispatch_labels", new_callable=AsyncMock):
            await session.handle_event({"type": "transcription.text.delta", "text": "We need "})
            await session.handle_event({"type": "turn.end"})
            self.assertEqual(state.segments, [])
            await session.handle_event({"type": "transcription.text.delta", "text": "fifty seats."})
            await session.handle_event({"type": "turn.start"})
            self.assertEqual(state.segments[0].text, "We need fifty seats.")
            await asyncio.sleep(0)
            await session.close()

    async def test_realtime_handshake(self):
        store = CallStore()
        session = VoxtralSession(store.create_call(), store, "client")
        socket = AsyncMock()
        socket.recv.side_effect = [json.dumps({"type": "session.created"}), json.dumps({"type": "session.updated"})]
        with patch("app.audio_gateway.connect", new_callable=AsyncMock, return_value=socket), \
             patch("app.audio_gateway.config.MISTRAL_API_KEY", "test-key"), \
             patch.object(session, "_listen", new_callable=AsyncMock):
            await session.connect()
            payload = json.loads(socket.send.call_args.args[0])
            self.assertEqual(payload["session"]["audio_format"], {"encoding": "pcm_s16le", "sample_rate": 16000})
            self.assertIn("turn_detection", payload["session"])
            await session.close()
            socket.close.assert_awaited_once()

if __name__ == "__main__":
    unittest.main()
