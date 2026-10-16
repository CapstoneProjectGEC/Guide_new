import React, { useState, useEffect } from "react";
import { Mic, Square, Loader2 } from "lucide-react";
import { audioService } from "@/services/audio";
import { AudioVisualizer } from "./AudioVisualizer";
import { UI_STRINGS } from "@/theme/tokens";

interface VoiceWidgetProps {
  language: "kn" | "en";
  isProcessing: boolean;
  isSpeaking: boolean;
  onAudioRecorded: (blob: Blob) => void;
  onError: (msg: string) => void;
}

export const VoiceWidget: React.FC<VoiceWidgetProps> = ({
  language,
  isProcessing,
  isSpeaking,
  onAudioRecorded,
  onError,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const t = UI_STRINGS[language];

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isRecording) {
      setRecordSeconds(0);
      timer = setInterval(() => {
        setRecordSeconds((sec) => sec + 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isRecording]);

  const handleStartRecording = async () => {
    if (!audioService.isRecordingSupported()) {
      onError(t.voiceUnavailable);
      return;
    }

    try {
      await audioService.startRecording();
      setIsRecording(true);
    } catch (err: any) {
      onError(err.message || t.voiceUnavailable);
    }
  };

  const handleStopRecording = async () => {
    if (!isRecording) return;
    try {
      setIsRecording(false);
      const res = await audioService.stopRecording();
      if (res.blob && res.blob.size > 0) {
        onAudioRecorded(res.blob);
      }
    } catch (err: any) {
      onError(err.message || "Failed to process audio recording.");
    }
  };

  const currentState = isRecording
    ? "listening"
    : isProcessing
    ? "processing"
    : isSpeaking
    ? "speaking"
    : "idle";

  return (
    <div className="flex items-center gap-3">
      {/* Visualizer active during listening, processing, or speaking */}
      {currentState !== "idle" && (
        <div className="flex items-center gap-2 animate-in fade-in duration-200">
          <AudioVisualizer state={currentState} />
          <span className="text-xs font-mono font-medium text-heritage-gold">
            {isRecording
              ? `00:${recordSeconds.toString().padStart(2, "0")}`
              : isProcessing
              ? t.processing
              : isSpeaking
              ? t.speaking
              : ""}
          </span>
        </div>
      )}

      {/* Main Mic Button */}
      {isRecording ? (
        <button
          onClick={handleStopRecording}
          aria-label="Stop recording voice query"
          className="relative p-3 rounded-full bg-heritage-terracotta text-white shadow-lg hover:scale-105 active:scale-95 transition-all focus:ring-2 focus:ring-offset-2 focus:ring-heritage-terracotta"
        >
          <Square className="w-5 h-5 fill-current" />
          <span className="absolute -inset-1 rounded-full border-2 border-heritage-terracotta/40 animate-ping pointer-events-none" />
        </button>
      ) : isProcessing ? (
        <button
          disabled
          aria-label="Processing voice query"
          className="p-3 rounded-full bg-heritage-sandstone dark:bg-heritage-carved-basalt text-heritage-gold shadow-md opacity-80"
        >
          <Loader2 className="w-5 h-5 animate-spin" />
        </button>
      ) : (
        <button
          onClick={handleStartRecording}
          aria-label="Ask using voice"
          title="Ask with Voice (STT)"
          className="p-3 rounded-full bg-heritage-gold hover:bg-heritage-gold-radiant text-heritage-brown shadow-md hover:scale-105 active:scale-95 transition-all focus:ring-2 focus:ring-offset-2 focus:ring-heritage-gold"
        >
          <Mic className="w-5 h-5" />
        </button>
      )}
    </div>
  );
};
