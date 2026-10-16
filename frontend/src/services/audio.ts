/**
 * Audio Recording and Playback Manager for Tourist Voice Interaction.
 * Handles microphone permissions, MediaRecorder chunk collection, and TTS audio playback.
 */

export interface AudioRecordingResult {
  blob: Blob;
  durationMs: number;
  mimeType: string;
}

export class AudioService {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private startTime: number = 0;
  private currentAudioElement: HTMLAudioElement | null = null;

  /**
   * Check if browser supports audio recording APIs.
   */
  isRecordingSupported(): boolean {
    return (
      typeof window !== "undefined" &&
      navigator.mediaDevices !== undefined &&
      typeof navigator.mediaDevices.getUserMedia === "function" &&
      typeof window.MediaRecorder !== "undefined"
    );
  }

  /**
   * Determine best supported MIME type for recording.
   */
  getSupportedMimeType(): string {
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/mp4",
      "audio/wav",
    ];

    if (typeof window !== "undefined" && window.MediaRecorder) {
      for (const candidate of candidates) {
        if (MediaRecorder.isTypeSupported(candidate)) {
          return candidate;
        }
      }
    }

    return "";
  }

  /**
   * Start recording from microphone.
   */
  async startRecording(): Promise<MediaStream> {
    if (!this.isRecordingSupported()) {
      throw new Error("Audio recording is not supported in this browser environment.");
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    const mimeType = this.getSupportedMimeType();
    this.mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    this.audioChunks = [];
    this.startTime = Date.now();

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };

    this.mediaRecorder.start(100); // 100ms slice interval
    return stream;
  }

  /**
   * Stop recording and return final audio blob.
   */
  async stopRecording(): Promise<AudioRecordingResult> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder) {
        return reject(new Error("No active recording session."));
      }

      this.mediaRecorder.onstop = () => {
        const durationMs = Date.now() - this.startTime;
        const mimeType = this.mediaRecorder?.mimeType || "audio/webm";
        const blob = new Blob(this.audioChunks, { type: mimeType });

        // Clean up audio tracks
        if (this.mediaRecorder && this.mediaRecorder.stream) {
          this.mediaRecorder.stream.getTracks().forEach((track) => track.stop());
        }
        this.mediaRecorder = null;
        this.audioChunks = [];

        resolve({ blob, durationMs, mimeType });
      };

      this.mediaRecorder.onerror = (event: any) => {
        reject(new Error(event.error?.message || "Recording error occurred."));
      };

      this.mediaRecorder.stop();
    });
  }

  /**
   * Play an audio URL (e.g. from synthesizeSpeech endpoint).
   */
  async playAudio(audioUrl: string, onEnded?: () => void): Promise<void> {
    this.stopPlayback();

    const audio = new Audio(audioUrl);
    this.currentAudioElement = audio;

    if (onEnded) {
      audio.onended = () => {
        this.currentAudioElement = null;
        onEnded();
      };
    }

    await audio.play();
  }

  /**
   * Stop current playback if active.
   */
  stopPlayback(): void {
    if (this.currentAudioElement) {
      this.currentAudioElement.pause();
      this.currentAudioElement.currentTime = 0;
      this.currentAudioElement = null;
    }
  }

  /**
   * Check if audio is currently playing.
   */
  isPlaying(): boolean {
    return this.currentAudioElement !== null && !this.currentAudioElement.paused;
  }
}

export const audioService = new AudioService();
