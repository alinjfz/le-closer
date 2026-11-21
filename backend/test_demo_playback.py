"""The full committed demo must keep playing even while model work is pending."""
import asyncio
import json
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app import main
from app.state import CallStore


class DemoPlaybackTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = CallStore()
        self.state = self.store.create_call(demo=True)
        self.script = json.loads((Path(__file__).parent / 'demo/script.json').read_text(encoding='utf-8'))

    async def asyncTearDown(self):
        await self.store.stop_jobs(self.state.call_id)

    async def test_script_retains_all_nineteen_turns(self):
        self.assertEqual(len(self.script), 19)
        self.assertEqual(sum(line['speaker'] == 'rep' for line in self.script), 9)
        self.assertEqual(sum(line['speaker'] == 'client' for line in self.script), 10)
        self.assertIn('pilot next week', self.script[-1]['text'])

    async def test_all_turns_appear_while_first_agent_is_still_waiting(self):
        queue = await self.store.bus.subscribe(self.state.call_id)
        release = asyncio.Event()
        processed = []
        async def slow_dispatch(state, segment):
            processed.append(segment.id)
            await release.wait()
        self.state.demo_status = 'playing'
        try:
            with patch.object(main, 'store', self.store), patch.object(main, '_dispatch', side_effect=slow_dispatch):
                playback = self.store.spawn(self.state.call_id, main._play_script(self.state, self.script, 0))
                async def wait_for_last_turn():
                    while True:
                        event = await queue.get()
                        if event['type'] == 'demo.progress' and event['payload']['current'] == 19:
                            return
                await asyncio.wait_for(wait_for_last_turn(), 1)
                self.assertEqual([{'speaker': seg.speaker, 'text': seg.text} for seg in self.state.segments], self.script)
                self.assertEqual(len(processed), 1)
                self.assertFalse(playback.done())
                self.assertEqual(self.state.demo_progress, {'current': 19, 'total': 19})
                release.set()
                await asyncio.wait_for(playback, 1)
                self.assertEqual(processed, [seg.id for seg in self.state.segments])
                self.assertEqual(self.state.demo_status, 'finished')
        finally:
            release.set()
            await self.store.bus.unsubscribe(self.state.call_id, queue)

    async def test_repeated_scripted_lines_are_not_dropped(self):
        script = [{'speaker': 'rep', 'text': 'This repeated line belongs in the script.'}] * 2
        with patch.object(main, 'store', self.store), patch.object(main, '_dispatch', new_callable=AsyncMock):
            await main._play_script(self.state, script, 0)
        self.assertEqual(len(self.state.segments), 2)

    async def test_cancelling_playback_stops_its_worker(self):
        entered, stopped = asyncio.Event(), asyncio.Event()
        async def blocked_dispatch(*args):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()
        with patch.object(main, 'store', self.store), patch.object(main, '_dispatch', side_effect=blocked_dispatch):
            playback = self.store.spawn(self.state.call_id, main._play_script(self.state, self.script, 0))
            await asyncio.wait_for(entered.wait(), 1)
            await self.store.stop_jobs(self.state.call_id)
        self.assertTrue(playback.cancelled())
        self.assertTrue(stopped.is_set())
        self.assertNotIn(self.state.call_id, self.store.jobs)

    async def test_periodic_agents_follow_processed_turn_not_transcript_length(self):
        from app.router import dispatch_labels
        from app.segments import make_segment
        for line in self.script:
            make_segment(self.state, line['speaker'], line['text'])
        with patch('app.fast_agents.flow_tracker.run', new_callable=AsyncMock) as flow, patch('app.fast_agents.mindmap.run', new_callable=AsyncMock) as mindmap:
            await dispatch_labels(self.state, self.store, self.state.segments[2], [])
        flow.assert_awaited_once()
        mindmap.assert_awaited_once()

    async def test_missing_script_does_not_substitute_three_lines(self):
        with patch.object(main, 'store', self.store), patch('pathlib.Path.read_text', side_effect=FileNotFoundError):
            with self.assertRaises(HTTPException) as result:
                await main.demo_play(self.state.call_id)
        self.assertEqual(result.exception.status_code, 503)
        self.assertEqual(self.state.segments, [])
        self.assertEqual(self.state.demo_status, 'idle')


if __name__ == '__main__':
    unittest.main()
