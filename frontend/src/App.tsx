import React, { useState, useEffect, useRef } from "react";
import { Layout } from "@/features/layout/Layout";
import { ChatContainer } from "@/features/chat/ChatContainer";
import { MessageInput } from "@/features/chat/MessageInput";
import { ChatMessage, Citation } from "@/types/api";
import { apiClient } from "@/services/api";
import { streamTouristMessage } from "@/services/streaming";
import { audioService } from "@/services/audio";
import { authService } from "@/services/auth";
import { AdminLogin } from "@/features/admin/AdminLogin";
import { AdminDashboard } from "@/features/admin/AdminDashboard";
import { AlertCircle, X } from "lucide-react";

export const App: React.FC = () => {
  const [isAdminMode, setIsAdminMode] = useState<boolean>(false);
  const [isAuthenticatedAdmin, setIsAuthenticatedAdmin] = useState<boolean>(authService.isAuthenticated());
  const [language, setLanguage] = useState<"kn" | "en">("kn");
  const [isDark, setIsDark] = useState<boolean>(() => {
    if (typeof window !== "undefined") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return false;
  });
  const [audioEnabled, setAudioEnabled] = useState<boolean>(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Synchronize admin auth state via in-memory listener
  useEffect(() => {
    const unsubscribe = authService.subscribe((isAuth) => {
      setIsAuthenticatedAdmin(isAuth);
    });
    return unsubscribe;
  }, []);

  // Sync dark mode class to html element
  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDark]);

  // Dismiss error banner after 6 seconds
  useEffect(() => {
    if (errorBanner) {
      const timer = setTimeout(() => setErrorBanner(null), 6000);
      return () => clearTimeout(timer);
    }
  }, [errorBanner]);

  // Create or refresh tourist session on mount
  useEffect(() => {
    let mounted = true;
    apiClient
      .createSession(undefined, language)
      .then((session) => {
        if (mounted) {
          setSessionId(session.id);
        }
      })
      .catch((err) => {
        // Soft fallback: session will auto-initiate on first message turn
        console.warn("Session pre-creation deferred:", err);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const handleNewSession = async () => {
    if (isStreaming) {
      abortControllerRef.current?.abort();
    }
    audioService.stopPlayback();
    setIsSpeaking(false);
    setMessages([]);
    setActiveCitation(null);

    try {
      const session = await apiClient.createSession(undefined, language);
      setSessionId(session.id);
    } catch {
      setSessionId(null);
    }
  };

  const handleSpeakText = async (text: string, lang: string) => {
    if (!text.trim()) return;
    try {
      setIsSpeaking(true);
      const { audioUrl } = await apiClient.synthesizeSpeech({
        text,
        language: lang,
      });

      await audioService.playAudio(audioUrl, () => {
        setIsSpeaking(false);
      });
    } catch (err: any) {
      setIsSpeaking(false);
      console.warn("TTS synthesis error:", err);
    }
  };

  const handleSendMessage = async (content: string, inputMode: "text" | "voice" = "text") => {
    if (!content.trim() || isStreaming || isProcessing) return;

    audioService.stopPlayback();
    setIsSpeaking(false);

    const userMessageId = `user-${Date.now()}`;
    const assistantMessageId = `asst-${Date.now() + 1}`;

    const userMsg: ChatMessage = {
      id: userMessageId,
      session_id: sessionId || "",
      role: "user",
      content,
      detected_language: language,
      input_mode: inputMode,
      is_grounded: true,
      created_at: new Date().toISOString(),
      citations: [],
    };

    const initialAssistantMsg: ChatMessage = {
      id: assistantMessageId,
      session_id: sessionId || "",
      role: "assistant",
      content: "",
      detected_language: language,
      input_mode: inputMode,
      is_grounded: true,
      created_at: new Date().toISOString(),
      citations: [],
    };

    setMessages((prev) => [...prev, userMsg, initialAssistantMsg]);
    setIsStreaming(true);
    setStreamingMessageId(assistantMessageId);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const streamUrl = `${apiClient.getApiBase()}/chat/stream`;
    let accumulatedContent = "";

    try {
      await streamTouristMessage(
        streamUrl,
        {
          session_id: sessionId,
          content,
          preferred_language: language,
          input_mode: inputMode,
        },
        {
          onToken: (token) => {
            accumulatedContent += token;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId ? { ...m, content: accumulatedContent } : m
              )
            );
          },
          onCitations: (citations) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId ? { ...m, citations } : m
              )
            );
          },
          onDone: (donePayload) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMessageId
                  ? {
                      ...m,
                      id: donePayload.message_id || m.id,
                      session_id: donePayload.session_id || m.session_id,
                      is_grounded: donePayload.is_grounded,
                      detected_language: donePayload.detected_language,
                      latency_ms: donePayload.latency_ms,
                    }
                  : m
              )
            );
            if (donePayload.session_id) {
              setSessionId(donePayload.session_id);
            }

            // Auto-speak answer if audio is enabled
            if (audioEnabled && accumulatedContent) {
              handleSpeakText(accumulatedContent, donePayload.detected_language || language);
            }
          },
          onError: (err) => {
            setErrorBanner(err.message || "An error occurred while streaming the answer.");
          },
        },
        controller.signal
      );
    } catch (err: any) {
      if (!controller.signal.aborted) {
        setErrorBanner(err.message || "Failed to receive response from the guide.");
      }
    } finally {
      setIsStreaming(false);
      setStreamingMessageId(null);
    }
  };

  const handleAudioRecorded = async (blob: Blob) => {
    setIsProcessing(true);
    try {
      // Transcribe user speech via offline faster-whisper STT
      const res = await apiClient.transcribeAudio(blob, language);
      setIsProcessing(false);

      if (res.is_silent || !res.text.trim()) {
        setErrorBanner(
          language === "kn"
            ? "ಯಾವುದೇ ಧ್ವನಿ ಗ್ರಹಿಸಲಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ."
            : "No speech detected. Please speak clearly into the microphone."
        );
        return;
      }

      // Automatically send transcribed question to chat stream
      await handleSendMessage(res.text, "voice");
    } catch (err: any) {
      setIsProcessing(false);
      setErrorBanner(err.message || "Voice transcription failed.");
    }
  };

  if (isAdminMode) {
    if (isAuthenticatedAdmin) {
      return <AdminDashboard onExit={() => setIsAdminMode(false)} />;
    }
    return (
      <AdminLogin
        onSuccess={() => setIsAuthenticatedAdmin(true)}
        onCancel={() => setIsAdminMode(false)}
      />
    );
  }

  return (
    <Layout
      language={language}
      onLanguageChange={setLanguage}
      audioEnabled={audioEnabled}
      onAudioToggle={() => {
        setAudioEnabled((prev) => !prev);
        if (audioEnabled) {
          audioService.stopPlayback();
          setIsSpeaking(false);
        }
      }}
      isDark={isDark}
      onThemeToggle={() => setIsDark((prev) => !prev)}
      onNewSession={handleNewSession}
      onSelectAttraction={(query) => handleSendMessage(query, "text")}
      activeCitation={activeCitation}
      onCloseCitation={() => setActiveCitation(null)}
      onOpenAdmin={() => setIsAdminMode(true)}
    >
      {/* Error notification banner */}
      {errorBanner && (
        <div
          role="alert"
          className="mx-4 mt-3 p-3 rounded-lg bg-heritage-terracotta/10 border border-heritage-terracotta/30 text-heritage-terracotta dark:text-red-300 text-xs flex items-center justify-between animate-in fade-in duration-200"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{errorBanner}</span>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            aria-label="Dismiss error"
            className="p-1 hover:bg-heritage-terracotta/20 rounded"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Conversation Stream */}
      <ChatContainer
        messages={messages}
        isStreaming={isStreaming}
        streamingMessageId={streamingMessageId}
        language={language}
        onSelectSuggestedQuestion={(text) => handleSendMessage(text, "text")}
        onCitationClick={setActiveCitation}
        onSpeakMessage={handleSpeakText}
      />

      {/* Message and Voice Input Footer */}
      <MessageInput
        language={language}
        isStreaming={isStreaming}
        isProcessing={isProcessing}
        isSpeaking={isSpeaking}
        onSendMessage={handleSendMessage}
        onAudioRecorded={handleAudioRecorded}
        onError={setErrorBanner}
      />
    </Layout>
  );
};

export default App;
