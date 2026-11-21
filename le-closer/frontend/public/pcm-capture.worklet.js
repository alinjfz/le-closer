/* 100 ms packets of mono PCM16 at the AudioContext's requested 16 kHz rate. */
class LeCloserPCM extends AudioWorkletProcessor {
  constructor() {
    super();
    this.samples = new Int16Array(1600);
    this.offset = 0;
    this.energy = 0;
  }
  process(inputs) {
    const channels = inputs[0];
    if (!channels || !channels.length) return true;
    for (let i = 0; i < channels[0].length; i++) {
      let sample = 0;
      for (const channel of channels) sample += channel[i];
      sample = Math.max(-1, Math.min(1, sample / channels.length));
      this.energy += sample * sample;
      this.samples[this.offset++] = sample < 0 ? sample * 32768 : sample * 32767;
      if (this.offset === this.samples.length) {
        this.port.postMessage({ pcm: this.samples.buffer, level: Math.sqrt(this.energy / this.offset) }, [this.samples.buffer]);
        this.samples = new Int16Array(1600);
        this.offset = 0;
        this.energy = 0;
      }
    }
    return true;
  }
}
registerProcessor("lecloser-pcm", LeCloserPCM);
