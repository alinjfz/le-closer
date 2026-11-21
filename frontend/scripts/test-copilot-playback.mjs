import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const require = createRequire(new URL('../package.json', import.meta.url));
async function load(source, rewrite = value => value) {
  const code = ts.transpileModule(fs.readFileSync(new URL(source, import.meta.url), 'utf8'), {
    compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ES2020 },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(rewrite(code)).toString('base64')}`);
}
const { CopilotPlayback } = await load('../src/lib/copilotPlayback.ts');
const { useCallStore, initialCall } = await load('../src/store/callStore.ts', code => code.replace('"zustand"', JSON.stringify(pathToFileURL(require.resolve('zustand')).href)));

function harness() {
  let now = 10000, id = 0;
  const timers = new Map();
  const waiting = [];
  let blocked = 0;
  const gate = new CopilotPlayback({
    now: () => now,
    setTimer(callback, delay) { const key = ++id; timers.set(key, { at: now + delay, callback }); return key; },
    clearTimer(key) { timers.delete(key); },
    onWaiting(value) { waiting.push(value); },
    onBlocked() { blocked++; },
  });
  function media() {
    return {
      paused: true, ended: false, currentTime: 0, plays: 0, pauses: 0,
      play() { this.plays++; this.paused = false; gate.onPlay(this); return Promise.resolve(); },
      pause() { if (this.paused) return; this.pauses++; this.paused = true; gate.onPause(this); },
    };
  }
  return {
    gate, media, waiting, timers,
    get now() { return now; }, get blocked() { return blocked; },
    advance(ms) {
      const target = now + ms;
      while (true) {
        const next = [...timers.entries()].sort((a, b) => a[1].at - b[1].at)[0];
        if (!next || next[1].at > target) break;
        now = next[1].at; timers.delete(next[0]); next[1].callback();
      }
      now = target;
    },
  };
}

// Initial playback waits a full two seconds; new text restarts the quiet period.
{
  const h = harness(), player = h.media();
  h.gate.attach(player, h.now);
  h.advance(1999); assert.equal(player.plays, 0);
  h.gate.transcriptActivity(h.now);
  h.advance(1999); assert.equal(player.plays, 0);
  h.advance(1); assert.equal(player.plays, 1);
  assert.equal(h.waiting.at(-1), false);
  h.gate.dispose(); assert.equal(h.timers.size, 0);
}

// If the last transcript is already quiet, a newly ready reply need not wait again.
{
  const h = harness(), player = h.media();
  h.advance(3000); h.gate.attach(player, 10000);
  assert.equal(player.plays, 1);
  h.gate.dispose();
}

// Speech resumes from its current position after conversation interrupts it.
{
  const h = harness(), player = h.media();
  h.gate.attach(player, h.now); h.advance(2000);
  player.currentTime = 12;
  h.gate.transcriptActivity(h.now);
  assert.equal(player.paused, true); assert.equal(h.waiting.at(-1), true);
  h.advance(1999); assert.equal(player.plays, 1);
  h.advance(1); assert.equal(player.plays, 2); assert.equal(player.currentTime, 12);
  player.pause(); // manual pause is not undone by another transcript update
  h.gate.transcriptActivity(h.now); h.advance(4000);
  assert.equal(player.plays, 2); assert.equal(h.timers.size, 0);
  h.gate.dispose();
}

// The native play control is gated too; muted/ended/disconnected queues are cancelled.
{
  const h = harness(), player = h.media();
  h.gate.attach(player, h.now);
  player.paused = false; h.gate.onPlay(player);
  assert.equal(player.paused, true);
  h.advance(2000); assert.equal(player.plays, 1);
  h.gate.transcriptActivity(h.now); h.gate.setActive(false);
  h.advance(5000); assert.equal(player.plays, 1); assert.equal(h.timers.size, 0);
  h.gate.onPlay(player); assert.equal(player.paused, true);
  h.gate.dispose();
}

// Replacing an answer or leaving the page cannot leave an older playback timer alive.
{
  const h = harness(), oldPlayer = h.media(), nextPlayer = h.media();
  h.gate.attach(oldPlayer, h.now); h.advance(1000);
  h.gate.attach(nextPlayer, h.now); h.advance(2000);
  assert.equal(oldPlayer.plays, 0); assert.equal(nextPlayer.plays, 1);
  h.gate.transcriptActivity(h.now); h.gate.dispose(); h.advance(5000);
  assert.equal(nextPlayer.plays, 1); assert.equal(h.timers.size, 0);
}

// Ended audio is not replayed; autoplay refusal leaves a recoverable manual control.
{
  const h = harness(), player = h.media();
  h.gate.attach(player, h.now); h.advance(2000);
  player.ended = true; player.paused = true; h.gate.onEnded(player);
  h.gate.transcriptActivity(h.now); h.advance(5000); assert.equal(player.plays, 1);
  h.gate.dispose();
  const denied = harness(), blockedPlayer = denied.media();
  blockedPlayer.play = () => Promise.reject(new Error('Autoplay blocked'));
  denied.gate.attach(blockedPlayer, denied.now); denied.advance(2000);
  await Promise.resolve(); assert.equal(denied.blocked, 1); assert.equal(denied.timers.size, 0);
  denied.gate.dispose();
}

// A conversation-triggered pause can abort an in-flight play promise without
// being misreported as autoplay denial or cancelling the later resume.
{
  const h = harness(), player = h.media();
  let rejectPlay;
  player.play = function () { this.plays++; this.paused = false; return new Promise((_, reject) => { rejectPlay = reject; }); };
  h.gate.attach(player, h.now); h.advance(2000);
  h.gate.transcriptActivity(h.now);
  const aborted = new Error('Interrupted by pause'); aborted.name = 'AbortError';
  rejectPlay(aborted); await Promise.resolve();
  assert.equal(h.blocked, 0);
  player.play = function () { this.plays++; this.paused = false; h.gate.onPlay(this); return Promise.resolve(); };
  h.advance(2000); assert.equal(player.plays, 2);
  h.gate.dispose();
}

// Real store events from either speaker postpone speech; translations and notes
// do not count as conversation activity. No real timers, media or sockets are used.
{
  const originalNow = Date.now;
  const h = harness(), player = h.media();
  Date.now = () => h.now;
  let unsubscribe;
  try {
    useCallStore.getState().setCall({ ...structuredClone(initialCall), call_id: 'quiet_test' });
    h.gate.attach(player, useCallStore.getState().lastTranscriptActivityAt);
    unsubscribe = useCallStore.subscribe((state, previous) => {
      if (state.lastTranscriptActivityAt !== previous.lastTranscriptActivityAt) h.gate.transcriptActivity(state.lastTranscriptActivityAt);
    });
    h.advance(1500);
    useCallStore.getState().applyEvent('transcript.delta', { speaker: 'rep', text: 'Still speaking' });
    h.advance(1500); assert.equal(player.plays, 0);
    useCallStore.getState().applyEvent('transcript.delta', { speaker: 'client', text: 'My turn' });
    h.advance(1500); assert.equal(player.plays, 0);
    const segment = { id: 's1', speaker: 'client', text: 'My turn', start_ms: 0, end_ms: 1 };
    useCallStore.getState().applyEvent('transcript.segment', segment);
    h.advance(1500);
    const lastSpeech = useCallStore.getState().lastTranscriptActivityAt;
    useCallStore.getState().applyEvent('transcript.translation', { ...segment, translation: 'Mon tour' });
    useCallStore.getState().applyEvent('notes.ready', { markdown: 'Notes' });
    assert.equal(useCallStore.getState().lastTranscriptActivityAt, lastSpeech);
    h.advance(500); assert.equal(player.plays, 1);
  } finally {
    unsubscribe?.(); h.gate.dispose(); useCallStore.getState().reset(); Date.now = originalNow;
  }
}
// Browser timer APIs require the Window receiver. Node timers and injected
// fake clocks tolerate a class instance, which hid this regression previously.
{
  const originalSetTimeout = globalThis.setTimeout;
  const originalClearTimeout = globalThis.clearTimeout;
  let nextId = 0;
  const timers = new Map();
  globalThis.setTimeout = function (callback, delay) {
    if (this !== globalThis) throw new TypeError('Illegal invocation');
    const id = ++nextId;
    timers.set(id, { callback, delay });
    return id;
  };
  globalThis.clearTimeout = function (id) {
    if (this !== globalThis) throw new TypeError('Illegal invocation');
    timers.delete(id);
  };
  let gate;
  try {
    gate = new CopilotPlayback({ now: () => 10000 });
    const player = { paused: true, ended: false, play: () => Promise.resolve(), pause() {} };
    assert.doesNotThrow(() => gate.attach(player, 10000));
    assert.equal(timers.size, 1);
    assert.equal([...timers.values()][0].delay, 2000);
    assert.doesNotThrow(() => gate.transcriptActivity(10000));
    assert.equal(timers.size, 1);
    assert.doesNotThrow(() => gate.dispose());
    assert.equal(timers.size, 0);
  } finally {
    try { gate?.dispose(); } finally {
      globalThis.setTimeout = originalSetTimeout;
      globalThis.clearTimeout = originalClearTimeout;
    }
  }
}
console.log('PASS: two-second silence, both transcript channels, partial/final text, interrupt/resume, manual controls, mute/disconnect cancellation, autoplay failure and timer cleanup');
