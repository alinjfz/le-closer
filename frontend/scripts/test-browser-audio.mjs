import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
const code = ts.transpileModule(fs.readFileSync(new URL('../src/lib/browserAudio.ts', import.meta.url), 'utf8'), {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ES2020 },
}).outputText;
const { startBrowserAudio } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
let sockets, contexts, nodes, stoppedTracks;
function reset(getStream) {
  sockets = []; contexts = []; nodes = []; stoppedTracks = 0;
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: {
    getDisplayMedia: getStream, getUserMedia: getStream,
  } } });
  globalThis.window = { location: { protocol: 'http:', host: 'localhost:5173' } };
  globalThis.MediaStream = class { constructor(tracks) { this.tracks = tracks; } };
  globalThis.WebSocket = class {
    static OPEN = 1; static CLOSING = 2;
    readyState = 0; bufferedAmount = 0; sent = [];
    constructor(url) { this.url = url; sockets.push(this); queueMicrotask(() => { this.readyState = 1; this.onopen?.(); }); }
    send(data) { this.sent.push(data); }
    close() { this.readyState = 3; this.onclose?.({ code: 1000 }); }
  };
  const graph = () => ({ connect() { return this; }, disconnect() {} });
  globalThis.AudioContext = class {
    state = 'running'; sampleRate = 16000; destination = {};
    audioWorklet = { addModule: async () => {} };
    constructor() { contexts.push(this); }
    async resume() {} async close() { this.state = 'closed'; }
    createMediaStreamSource() { return graph(); }
    createGain() { return { ...graph(), gain: { value: 1 } }; }
  };
  globalThis.AudioWorkletNode = class {
    port = {}; constructor() { nodes.push(this); } connect() { return graph(); } disconnect() {}
  };
}
function media(withAudio = true) {
  const video = { stop() { stoppedTracks++; }, getSettings: () => ({ displaySurface: 'browser' }) };
  const audio = { stop() { stoppedTracks++; } };
  return { getTracks: () => withAudio ? [video, audio] : [video], getAudioTracks: () => withAudio ? [audio] : [], getVideoTracks: () => [video] };
}
function begin(source = 'tab') {
  const states = [], errors = [];
  const handle = startBrowserAudio({ callId: 'call_test', source, onState: s => states.push(s), onLevel() {}, onError: e => { if(e) errors.push(e); } });
  return { ...handle, states, errors };
}
reset(async () => media());
let capture = begin();
await capture.ready;
assert.equal(capture.states.at(-1), 'streaming');
assert.match(sockets[0].url, /\/client$/);
const pcm = new Int16Array([1, -1]).buffer;
nodes[0].port.onmessage({ data: { pcm, level: 0.3 } });
assert.equal(sockets[0].sent[0], pcm);
capture.stop();
assert.equal(stoppedTracks, 2);
assert.equal(contexts[0].state, 'closed');
assert.equal(sockets[0].readyState, 3);

reset(async () => media(false));
capture = begin(); await capture.ready;
assert.match(capture.errors[0], /No audio was shared/);
assert.equal(stoppedTracks, 1);
assert.equal(sockets.length, 0);

let resolvePrompt;
reset(() => new Promise(resolve => { resolvePrompt = resolve; }));
capture = begin(); capture.stop(); resolvePrompt(media()); await capture.ready;
assert.equal(stoppedTracks, 2);
assert.equal(contexts.length, 0);

reset(async () => media());
capture = begin('microphone'); await capture.ready;
assert.match(sockets[0].url, /\/rep$/);
sockets[0].onclose({ code: 1011 });
assert.equal(capture.states.at(-1), 'error');
assert.equal(stoppedTracks, 2);
assert.equal(contexts[0].state, 'closed');

let Processor, packet;
vm.runInNewContext(fs.readFileSync(new URL('../public/pcm-capture.worklet.js', import.meta.url), 'utf8'), {
  AudioWorkletProcessor: class { constructor() { this.port = { postMessage: value => { packet = value; } }; } },
  registerProcessor: (_, processor) => { Processor = processor; },
});
const processor = new Processor();
processor.process([[new Float32Array(1600).fill(0.5), new Float32Array(1600).fill(-0.25)]]);
assert.equal(packet.pcm.byteLength, 3200);
assert.equal(new Int16Array(packet.pcm)[0], Math.trunc(0.125 * 32767));
assert.equal(packet.level, 0.125);
console.log('PASS: PCM forwarding, mono conversion, microphone channel, missing audio, pending prompt cancellation, socket failure and resource cleanup');
