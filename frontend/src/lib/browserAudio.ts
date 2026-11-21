export type AudioSource = "tab" | "microphone";
export type CaptureState = "idle" | "selecting" | "connecting" | "streaming" | "error";
export interface CaptureHandle { ready: Promise<void>; stop: () => void }
interface Options {
  callId: string;
  source: AudioSource;
  onState: (state: CaptureState) => void;
  onLevel: (level: number) => void;
  onError: (message: string) => void;
}

/** Each capture owns its tracks, audio graph and socket, including pending prompts. */
export function startBrowserAudio(options: Options): CaptureHandle {
  let stopped = false;
  let stream: MediaStream | undefined;
  let context: AudioContext | undefined;
  let socket: WebSocket | undefined;
  let node: AudioWorkletNode | undefined;
  let timeout: ReturnType<typeof setTimeout> | undefined;
  let cancelConnection: (() => void) | undefined;

  const release = () => {
    stopped = true;
    clearTimeout(timeout);
    cancelConnection?.();
    cancelConnection = undefined;
    if (node) { node.port.onmessage = null; node.disconnect(); }
    stream?.getTracks().forEach((track) => { track.onended = null; track.stop(); });
    if (socket && socket.readyState < WebSocket.CLOSING) socket.close();
    if (context && context.state !== "closed") void context.close().catch(() => {});
    options.onLevel(0);
  };
  const stop = () => {
    if (stopped) return;
    release();
    options.onState("idle");
  };
  const fail = (error: unknown) => {
    if (stopped) return;
    release();
    const name = error instanceof DOMException ? error.name : "";
    options.onError(name === "NotAllowedError"
      ? "Sharing was cancelled or denied. Click the capture button to try again."
      : error instanceof Error ? error.message : "Audio capture failed.");
    options.onState("error");
  };

  options.onError("");
  options.onState("selecting");
  // Request media directly from the click handler, before awaiting any network work.
  const ready = (async () => {
    if (!navigator.mediaDevices) throw new Error("Open the dashboard on localhost or HTTPS in Chrome or Edge.");
    if (options.source === "tab") {
      if (!navigator.mediaDevices.getDisplayMedia) throw new Error("Tab capture is unavailable. Open this dashboard in Chrome or Edge.");
      stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: "browser" },
        audio: { suppressLocalAudioPlayback: false, echoCancellation: false, noiseSuppression: false, autoGainControl: false },
        selfBrowserSurface: "exclude",
        systemAudio: "exclude",
        surfaceSwitching: "exclude",
      } as DisplayMediaStreamOptions);
    } else {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }, video: false,
      });
    }
    if (stopped) { stream.getTracks().forEach((track) => track.stop()); return; }
    if (!stream.getAudioTracks().length) throw new Error("No audio was shared. Select Chrome Tab → your Google Meet tab and enable Share tab audio.");
    if (options.source === "tab") {
      const surface = stream.getVideoTracks()[0]?.getSettings().displaySurface;
      if (surface && surface !== "browser") throw new Error("Select a Chrome Tab rather than a window or entire screen, and enable Share tab audio.");
    }
    stream.getTracks().forEach((track) => { track.onended = stop; });
    options.onState("connecting");
    context = new AudioContext({ sampleRate: 16000 });
    if (context.sampleRate !== 16000) throw new Error("This browser could not initialize 16 kHz audio. Try Chrome or Edge.");
    await context.resume();
    if (stopped) return;
    await context.audioWorklet.addModule("/pcm-capture.worklet.js");
    if (stopped) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const channel = options.source === "tab" ? "client" : "rep";
    socket = new WebSocket(`${protocol}://${window.location.host}/ws/audio/${encodeURIComponent(options.callId)}/${channel}`);
    await new Promise<void>((resolve, reject) => {
      const rejectConnection = () => reject(new Error("Audio connection was stopped."));
      cancelConnection = rejectConnection;
      timeout = setTimeout(() => reject(new Error("Audio connection timed out. Check that the Docker backend is healthy.")), 10000);
      socket!.onopen = () => { clearTimeout(timeout); cancelConnection = undefined; resolve(); };
      socket!.onerror = () => { reject(new Error("Audio connection failed. Check the dashboard activity log.")); fail(new Error("Audio connection failed. Check the dashboard activity log.")); };
      socket!.onclose = (event) => {
        rejectConnection();
        if (!stopped) fail(new Error(event.code === 4409
          ? "This audio channel is already in use. Stop the other capture first."
          : "Transcription connection closed. Check the activity log, then start capture again."));
      };
    });
    if (stopped) return;
    node = new AudioWorkletNode(context, "lecloser-pcm", { channelCount: 1, channelCountMode: "explicit" });
    node.port.onmessage = (event: MessageEvent<{ pcm: ArrayBuffer; level: number }>) => {
      if (stopped || socket?.readyState !== WebSocket.OPEN) return;
      if (socket.bufferedAmount > 96000) { fail(new Error("Audio upload is falling behind. Check your connection and retry.")); return; }
      options.onLevel(event.data.level);
      socket.send(event.data.pcm);
    };
    const source = context.createMediaStreamSource(new MediaStream(stream.getAudioTracks()));
    const silent = context.createGain();
    silent.gain.value = 0;
    source.connect(node).connect(silent).connect(context.destination);
    options.onState("streaming");
  })().catch(fail);
  return { ready, stop };
}
