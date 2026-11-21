/** Gate spoken answers on a shared two-channel transcript quiet period. */
export interface SpeechMedia {
  paused: boolean;
  ended: boolean;
  play(): Promise<void>;
  pause(): void;
}

interface PlaybackOptions {
  now?: () => number;
  setTimer?: (callback: () => void, ms: number) => ReturnType<typeof setTimeout>;
  clearTimer?: (timer: ReturnType<typeof setTimeout>) => void;
  onWaiting?: (waiting: boolean) => void;
  onBlocked?: () => void;
}

export class CopilotPlayback {
  static readonly SILENCE_MS = 2000;
  private media: SpeechMedia | null = null;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private lastTranscriptAt: number;
  private requested = false;
  private active = true;
  private automaticPause = false;
  private disposed = false;
  private readonly now;
  private readonly setTimer;
  private readonly clearTimer;

  constructor(private readonly options: PlaybackOptions = {}) {
    this.now = options.now || (() => Date.now());
    // Browser timer functions require the Window receiver. Calling a saved
    // reference as this.setTimer(...) would bind it to CopilotPlayback instead.
    this.setTimer = options.setTimer || ((callback, ms) => globalThis.setTimeout(callback, ms));
    this.clearTimer = options.clearTimer || ((timer) => globalThis.clearTimeout(timer));
    this.lastTranscriptAt = this.now();
  }

  transcriptActivity(at: number) {
    this.lastTranscriptAt = Math.max(this.lastTranscriptAt, at);
    if (!this.requested || this.disposed) return;
    this.pauseAutomatically();
    this.schedule();
  }

  setActive(active: boolean) {
    this.active = active;
    if (!active) this.stop();
  }

  attach(media: SpeechMedia, lastTranscriptAt: number) {
    this.detach();
    if (this.disposed) return;
    this.media = media;
    this.lastTranscriptAt = Math.max(this.lastTranscriptAt, lastTranscriptAt);
    this.requested = this.active;
    this.schedule();
  }

  detach() {
    this.stop();
    this.media = null;
    this.automaticPause = false;
  }

  /** Also guard the browser's native play button against interrupting speech. */
  onPlay(media: SpeechMedia) {
    if (media !== this.media || this.disposed) return;
    this.requested = this.active;
    if (!this.active || this.remaining() > 0) {
      this.pauseAutomatically();
      this.schedule();
    } else {
      this.cancelTimer();
      this.options.onWaiting?.(false);
    }
  }

  onPause(media: SpeechMedia) {
    if (media !== this.media || this.disposed) return;
    if (this.automaticPause) {
      this.automaticPause = false;
      return;
    }
    // A manual pause is respected; new transcript activity must not resume it.
    this.requested = false;
    this.cancelTimer();
    this.options.onWaiting?.(false);
  }

  onEnded(media: SpeechMedia) {
    if (media !== this.media) return;
    this.requested = false;
    this.cancelTimer();
    this.options.onWaiting?.(false);
  }

  dispose() {
    this.detach();
    this.disposed = true;
  }

  private remaining() {
    return Math.max(0, CopilotPlayback.SILENCE_MS - (this.now() - this.lastTranscriptAt));
  }

  private pauseAutomatically() {
    if (this.media && !this.media.paused) {
      this.automaticPause = true;
      this.media.pause();
    }
  }

  private stop() {
    this.requested = false;
    this.cancelTimer();
    this.pauseAutomatically();
    this.options.onWaiting?.(false);
  }

  private cancelTimer() {
    if (this.timer !== undefined) this.clearTimer(this.timer);
    this.timer = undefined;
  }

  private schedule() {
    this.cancelTimer();
    if (!this.active || !this.requested || !this.media || this.media.ended || this.disposed) {
      this.options.onWaiting?.(false);
      return;
    }
    const remaining = this.remaining();
    this.options.onWaiting?.(remaining > 0);
    if (remaining > 0) {
      this.timer = this.setTimer(() => { this.timer = undefined; this.schedule(); }, remaining);
      return;
    }
    const media = this.media;
    void media.play().catch((error: unknown) => {
      if (this.media !== media || this.disposed || !this.requested || !this.active) return;
      if (error instanceof Error && error.name === "AbortError" && this.remaining() > 0) return;
      this.requested = false;
      this.cancelTimer();
      this.options.onWaiting?.(false);
      this.options.onBlocked?.();
    });
  }
}
