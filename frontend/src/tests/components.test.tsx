import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Header } from "../features/layout/Header";
import { MessageBubble } from "../features/chat/MessageBubble";
import { SuggestedQuestions } from "../features/chat/SuggestedQuestions";
import { CitationDrawer } from "../features/citations/CitationDrawer";
import { MessageInput } from "../features/chat/MessageInput";
import { ChatMessage, Citation } from "../types/api";

describe("Frontend UI Components", () => {
  it("Header renders monument title and handles language toggle", () => {
    const onLanguageChange = vi.fn();
    render(
      <Header
        language="kn"
        onLanguageChange={onLanguageChange}
        audioEnabled={true}
        onAudioToggle={vi.fn()}
        isDark={false}
        onThemeToggle={vi.fn()}
        onToggleSidebar={vi.fn()}
        onToggleMap={vi.fn()}
      />
    );

    // Should display Kannada title by default
    expect(screen.getByText("ಬೇಲೂರು ಶ್ರೀ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ")).toBeInTheDocument();

    // Clicking language toggle should call onLanguageChange with 'en'
    const langBtn = screen.getByLabelText("Switch language between Kannada and English");
    fireEvent.click(langBtn);
    expect(onLanguageChange).toHaveBeenCalledWith("en");
  });

  it("MessageBubble renders assistant content, verification badge, and citations", () => {
    const mockCitation: Citation = {
      chunk_id: "chk-99",
      document_id: "Temple_info.pdf",
      page_number: 4,
      section_heading: "Sculptures",
      relevance_score: 0.96,
      snippet: "Darpana Sundari holds a hand mirror.",
    };

    const mockMsg: ChatMessage = {
      id: "asst-1",
      session_id: "sess-1",
      role: "assistant",
      content: "The temple has 42 Madanika bracket figures.",
      detected_language: "en",
      input_mode: "text",
      is_grounded: true,
      created_at: new Date().toISOString(),
      citations: [mockCitation],
    };

    const onCitationClick = vi.fn();
    render(
      <MessageBubble
        message={mockMsg}
        language="en"
        onCitationClick={onCitationClick}
      />
    );

    expect(screen.getByText("The temple has 42 Madanika bracket figures.")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();

    const citationBadge = screen.getByText("Source [1: p.4]");
    expect(citationBadge).toBeInTheDocument();

    fireEvent.click(citationBadge);
    expect(onCitationClick).toHaveBeenCalledWith(mockCitation);
  });

  it("MessageBubble renders properly localized Kannada labels in Kannada mode", () => {
    const mockCitation: Citation = {
      chunk_id: "chk-100",
      document_id: "Temple_info.pdf",
      page_number: 1,
      section_heading: "History",
      relevance_score: 0.98,
      snippet: "King Vishnuvardhana built the temple in 1117 CE.",
    };

    const mockMsgKn: ChatMessage = {
      id: "asst-kn-1",
      session_id: "sess-kn-1",
      role: "assistant",
      content: "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಹೊಯ್ಸಳ ರಾಜ ವಿಷ್ಣುವರ್ಧನನು ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದನು.",
      detected_language: "kn",
      input_mode: "text",
      is_grounded: true,
      created_at: new Date().toISOString(),
      citations: [mockCitation],
    };

    render(
      <MessageBubble
        message={mockMsgKn}
        language="kn"
        onCitationClick={vi.fn()}
      />
    );

    expect(screen.getByText("ಬೇಲೂರು ಪರಂಪರೆ ಮಾರ್ಗದರ್ಶಿ")).toBeInTheDocument();
    expect(screen.getByText("ಪರಿಶೀಲಿತ")).toBeInTheDocument();
    expect(screen.getByText("ಉಲ್ಲೇಖಿತ ಮೂಲಗಳು:")).toBeInTheDocument();
    expect(screen.getByText("ಮೂಲ [1: p.1]")).toBeInTheDocument();
    expect(screen.getByText("ಪ್ರತಿ ಮಾಡಿಕೊಳ್ಳಿ")).toBeInTheDocument();
    expect(screen.getByText("ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಹೊಯ್ಸಳ ರಾಜ ವಿಷ್ಣುವರ್ಧನನು ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದನು.")).toBeInTheDocument();
  });

  it("SuggestedQuestions renders cards and fires click callback", () => {
    const onSelect = vi.fn();
    render(<SuggestedQuestions language="en" onSelectQuestion={onSelect} />);

    const builderQuestion = screen.getByText("Who built the Chennakeshava Temple at Belur and when?");
    expect(builderQuestion).toBeInTheDocument();

    fireEvent.click(builderQuestion);
    expect(onSelect).toHaveBeenCalledWith("Who built the Chennakeshava Temple at Belur and when?");
  });

  it("CitationDrawer renders chunk excerpt and relevance percentage", () => {
    const mockCitation: Citation = {
      chunk_id: "chk-88",
      document_id: "Temple_info.pdf",
      page_number: 5,
      section_heading: "Architecture",
      relevance_score: 0.94,
      snippet: "Chloritic schist or soapstone allows intricate carving.",
    };

    render(
      <CitationDrawer
        citation={mockCitation}
        isOpen={true}
        onClose={vi.fn()}
        language="en"
      />
    );

    expect(screen.getByText("Temple_info.pdf")).toBeInTheDocument();
    expect(screen.getByText(/94% Match/)).toBeInTheDocument();
    expect(
      screen.getByText('"Chloritic schist or soapstone allows intricate carving."')
    ).toBeInTheDocument();
  });

  it("MessageInput supports Kannada Unicode input and submit via button", () => {
    const onSend = vi.fn();
    render(
      <MessageInput
        language="kn"
        isStreaming={false}
        isProcessing={false}
        isSpeaking={false}
        onSendMessage={onSend}
        onAudioRecorded={vi.fn()}
        onError={vi.fn()}
      />
    );

    const textarea = screen.getByPlaceholderText(/ಇತಿಹಾಸ, ವಾಸ್ತುಶಿಲ್ಪ/);
    fireEvent.change(textarea, { target: { value: "ದರ್ಪಣ ಸುಂದರಿಯ ಹಿರಿಮೆ ಏನು?" } });

    const sendBtn = screen.getByLabelText("ಕಳುಹಿಸಿ");
    fireEvent.click(sendBtn);

    expect(onSend).toHaveBeenCalledWith("ದರ್ಪಣ ಸುಂದರಿಯ ಹಿರಿಮೆ ಏನು?", "text");
  });

  it("MessageInput disables submission while streaming", () => {
    const onSend = vi.fn();
    render(
      <MessageInput
        language="en"
        isStreaming={true}
        isProcessing={false}
        isSpeaking={false}
        onSendMessage={onSend}
        onAudioRecorded={vi.fn()}
        onError={vi.fn()}
      />
    );

    const textarea = screen.getByRole("textbox");
    expect(textarea).toBeDisabled();

    const sendBtn = screen.getByRole("button", { name: "Send" });
    expect(sendBtn).toBeDisabled();
  });
});
