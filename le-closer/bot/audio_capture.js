/* Le Closer bot — consent-gated in-page audio capture for the Meet tab.
 *
 * PRIVACY: this only runs after (a) the rep confirmed recording consent on the
 * Le Closer setup screen and (b) the client agreed on the call ("May I record
 * this call?"). The bot announces itself in the Meet chat before capturing.
 * Captures incoming WebRTC audio tracks from the meeting, converts
 * to 16-bit PCM mono 16 kHz in an AudioWorklet, and ships base64 chunks to
 * Python via the exposed window.__leCloserSendPCM() binding (Playwright
 * expose_function), which forwards them to the Le Closer backend WebSocket.
 * Avoids mixed-content issues of opening ws:// from an https:// page.
 */
(async () => {
  if (window.__leCloserCapture) return "already-capturing";
  if (!window.__leCloserConsentGiven) return "consent-required";
  window.__leCloserCapture = true;

  const ctx = new AudioContext({ sampleRate: 16000 });
  await ctx.resume();
  window.__leCloserAudioChunks = 0;

  const workletCode = `
    class PCM extends AudioWorkletProcessor {
      constructor() { super(); this.buf = []; }
      process(inputs) {
        const ch = inputs[0][0];
        if (ch) {
          const out = new Int16Array(ch.length);
          for (let i = 0; i < ch.length; i++) {
            const s = Math.max(-1, Math.min(1, ch[i]));
            out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }
          this.buf.push(out);
          if (this.buf.length >= 10) {
            let len = 0; for (const b of this.buf) len += b.length;
            const merged = new Int16Array(len); let o = 0;
            for (const b of this.buf) { merged.set(b, o); o += b.length; }
            this.buf = [];
            const bytes = new Uint8Array(merged.buffer);
            let bin = ''; const CH = 0x8000;
            for (let i = 0; i < bytes.length; i += CH)
              bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
            this.port.postMessage(btoa(bin));
          }
        }
        return true;
      }
    }
    registerProcessor('pcm', PCM);
  `;
  const blob = new Blob([workletCode], { type: "application/javascript" });
  await ctx.audioWorklet.addModule(URL.createObjectURL(blob));

  const node = new AudioWorkletNode(ctx, "pcm", { channelCount: 1, channelCountMode: "explicit" });
  node.port.onmessage = (e) => {
    window.__leCloserAudioChunks++;
    if (typeof window.__leCloserSendPCM === "function") window.__leCloserSendPCM(e.data);
  };
  // Audio graph mixes remote receivers to mono; keep the output silent.
  const silent = ctx.createGain();
  silent.gain.value = 0;
  node.connect(silent).connect(ctx.destination);
  const sources = new Map();
  const attach = () => {
    for (const peer of window.__leCloserPeers || []) {
      for (const receiver of peer.getReceivers()) {
        const track = receiver.track;
        if (!track || track.kind !== "audio" || track.readyState !== "live" || sources.has(track.id)) continue;
        const source = ctx.createMediaStreamSource(new MediaStream([track]));
        source.connect(node);
        sources.set(track.id, source);
      }
    }
  };
  attach();
  const timer = setInterval(attach, 500);
  window.addEventListener("pagehide", () => {
    clearInterval(timer);
    ctx.close();
    window.__leCloserCapture = false;
  }, { once: true });
  return "capturing";
})();
