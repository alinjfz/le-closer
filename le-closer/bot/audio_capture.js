/* Le Closer bot — consent-gated in-page audio capture for the Meet tab.
 *
 * PRIVACY: this only runs after (a) the rep confirmed recording consent on the
 * Le Closer setup screen and (b) the client agreed on the call ("May I record
 * this call?"). The bot announces itself in the Meet chat before capturing.
 * Captures the meeting tab audio via getDisplayMedia({audio:true}), converts
 * to 16-bit PCM mono 16 kHz in an AudioWorklet, and ships base64 chunks to
 * Python via the exposed window.__leCloserSendPCM() binding (Playwright
 * expose_function), which forwards them to the Le Closer backend WebSocket.
 * Avoids mixed-content issues of opening ws:// from an https:// page.
 */
(async () => {
  if (window.__leCloserCapture) return "already-capturing";
  if (!window.__leCloserConsentGiven) return "consent-required";
  window.__leCloserCapture = true;

  const stream = await navigator.mediaDevices.getDisplayMedia({
    video: true,
    audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
  });
  const audioTrack = stream.getAudioTracks()[0];
  if (!audioTrack) throw new Error("no audio track — tab audio capture blocked");
  stream.getVideoTracks().forEach((t) => t.stop());

  const ctx = new AudioContext({ sampleRate: 16000 });
  const src = ctx.createMediaStreamSource(new MediaStream([audioTrack]));

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
            port.postMessage(btoa(bin));
          }
        }
        return true;
      }
    }
    registerProcessor('pcm', PCM);
  `;
  const blob = new Blob([workletCode], { type: "application/javascript" });
  await ctx.audioWorklet.addModule(URL.createObjectURL(blob));

  const node = new AudioWorkletNode(ctx, "pcm");
  node.port.onmessage = (e) => {
    if (typeof window.__leCloserSendPCM === "function") window.__leCloserSendPCM(e.data);
  };
  src.connect(node);
  node.connect(ctx.destination);

  audioTrack.onended = () => { window.__leCloserCapture = false; };
  return "capturing";
})();
