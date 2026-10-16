/**
 * Karnataka Heritage Design System Tokens & Verifiable Temple Metadata.
 * Strictly aligned with Design.md and verified historical content from Temple_info.pdf.
 */

export const HERITAGE_COLORS = {
  templeGold: "#D4AF37",
  templeGoldRadiant: "#E5C058",
  heritageBrown: "#2C1810",
  soapstoneGrey: "#4A4A4A",
  ivory: "#FDFBF7",
  midnightBasalt: "#120E0C",
  deepStone: "#1C1614",
  carvedBasalt: "#241C1A",
  softSandstone: "#F7F3EB",
  warmMarble: "#F5EBE6",
  mutedUmber: "#665C54",
  weatheredStone: "#A89F91",
  forestGreen: "#2D6A4F",
  terracottaRed: "#9B2226",
} as const;

export interface SuggestedQuestion {
  id: string;
  category: "history" | "architecture" | "sculpture" | "visitor";
  textEn: string;
  textKn: string;
}

export const SUGGESTED_QUESTIONS: SuggestedQuestion[] = [
  {
    id: "builder",
    category: "history",
    textEn: "Who built the Chennakeshava Temple at Belur and when?",
    textKn: "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?",
  },
  {
    id: "architecture",
    category: "architecture",
    textEn: "What are the unique architectural features of Hoysala temples?",
    textKn: "ಹೊಯ್ಸಳ ವಾಸ್ತುಶಿಲ್ಪದ ವಿಶಿಷ್ಟ ಲಕ್ಷಣಗಳು ಯಾವುವು?",
  },
  {
    id: "madanika",
    category: "sculpture",
    textEn: "Tell me about the Madanika bracket figures (bracket sculptures).",
    textKn: "ಮದನಿಕಾ ಅಥವಾ ಶಿಲಾಬಾಲಿಕೆಯರ ಶಿಲ್ಪಗಳ ಬಗ್ಗೆ ತಿಳಿಸಿ.",
  },
  {
    id: "darpana-sundari",
    category: "sculpture",
    textEn: "What is Darpana Sundari (the lady with the mirror)?",
    textKn: "ದರ್ಪಣ ಸುಂದರಿ ಶಿಲ್ಪದ ಹಿರಿಮೆ ಏನು?",
  },
  {
    id: "soapstone",
    category: "architecture",
    textEn: "Why did Hoysala artisans use chloritic schist (soapstone)?",
    textKn: "ಹೊಯ್ಸಳ ಶಿಲ್ಪಿಗಳು ಬಳಪದ ಕಲ್ಲನ್ನು (ಸೋಪ್‌ಸ್ಟೋನ್) ಏಕೆ ಬಳಸಿದರು?",
  },
  {
    id: "navaranga",
    category: "architecture",
    textEn: "What is special about the Navaranga central pillar ceiling?",
    textKn: "ನವರಂಗ ಮಂಟಪದ ಕಂಬಗಳು ಮತ್ತು ಛಾವಣಿಯ ವಿಶೇಷತೆ ಏನು?",
  },
];

export interface TempleAttraction {
  id: string;
  nameEn: string;
  nameKn: string;
  descriptionEn: string;
  descriptionKn: string;
  lat: number;
  lng: number;
  highlight: string;
}

export const BELUR_ATTRACTIONS: TempleAttraction[] = [
  {
    id: "main-sanctum",
    nameEn: "Chennakeshava Main Sanctum (Garbhagriha)",
    nameKn: "ಚೆನ್ನಕೇಶವ ಮುಖ್ಯ ಗರ್ಭಗೃಹ",
    descriptionEn: "Home to the 6-foot tall standing icon of Lord Vijayanarayana / Chennakeshava with 4 hands holding the shankha, chakra, gada, and padma.",
    descriptionKn: "ಶಂಖ, ಚಕ್ರ, ಗದಾ, ಪದ್ಮಗಳನ್ನು ಧರಿಸಿದ ೬ ಅಡಿ ಎತ್ತರದ ಭವ್ಯ ವಿಜಯನಾರಾಯಣ / ಚೆನ್ನಕೇಶವ ವಿಗ್ರಹ ನೆಲೆಸಿರುವ ಸ್ಥಳ.",
    lat: 13.1623,
    lng: 75.8596,
    highlight: "Primary Sanctum",
  },
  {
    id: "navaranga-hall",
    nameEn: "Navaranga (Hypostyle Hall)",
    nameKn: "ನವರಂಗ ಮಂಟಪ",
    descriptionEn: "Enclosed mantapa supported by lathe-turned star-shaped soapstone pillars, including the legendary Narasimha pillar.",
    descriptionKn: "ನರಸಿಂಹ ಸ್ತಂಭ ಸೇರಿದಂತೆ ನಯವಾಗಿ ತಿರುಗಿಸಿದ ಕಲ್ಲಿನ ಕಂಬಗಳುಳ್ಳ ಭವ್ಯ ಸಭಾಂಗಣ.",
    lat: 13.1624,
    lng: 75.8598,
    highlight: "Lathe-turned Pillars",
  },
  {
    id: "darpana-sundari",
    nameEn: "Darpana Sundari Bracket Figure",
    nameKn: "ದರ್ಪಣ ಸುಂದರಿ ಶಿಲಾಬಾಲಿಕೆ",
    descriptionEn: "World-famous bracket figure depicting a maiden admiring her beauty in a hand mirror, carved with extraordinary precision.",
    descriptionKn: "ಕೈಗನ್ನಡಿ ಹಿಡಿದು ತನ್ನ ಸೌಂದರ್ಯವನ್ನು ಕಣ್ತುಂಬಿಕೊಳ್ಳುವ ವಿಶ್ವಪ್ರಸಿದ್ಧ ಶಿಲಾಬಾಲಿಕೆ ಶಿಲ್ಪ.",
    lat: 13.1625,
    lng: 75.8595,
    highlight: "Bracket Sculpture #2",
  },
  {
    id: "kappe-chennigraya",
    nameEn: "Kappe Chennigraya Shrine",
    nameKn: "ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ ಗುಡಿ",
    descriptionEn: "Consecrated by Queen Shantala Devi simultaneously with the main temple, featuring a parallel sanctum.",
    descriptionKn: "ಶಾಂತಲಾ ದೇವಿಯವರಿಂದ ಪ್ರತಿಷ್ಠಾಪಿಸಲ್ಪಟ್ಟ ಪಕ್ಕದ ಸುಂದರ ದೇವಾಲಯ.",
    lat: 13.1621,
    lng: 75.8593,
    highlight: "Shantala Devi Shrine",
  },
  {
    id: "stepped-pushkarani",
    nameEn: "Vasudeva Theertha (Pushkarani)",
    nameKn: "ವಾಸುದೇವ ತೀರ್ಥ (ಪುಷ್ಕರಣಿ)",
    descriptionEn: "Historic stepped water tank situated in the northeast precinct, used for ceremonial temple ablutions.",
    descriptionKn: "ದೇವಾಲಯದ ಈಶಾನ್ಯ ಭಾಗದಲ್ಲಿರುವ ಸುಂದರವಾದ ಮೆಟ್ಟಿಲುಗಳ ಐತಿಹಾಸಿಕ ಕಲ್ಯಾಣಿ.",
    lat: 13.1628,
    lng: 75.8603,
    highlight: "Sacred Stepped Tank",
  },
];

export const UI_STRINGS = {
  en: {
    siteTitle: "Smart Tourist Guide",
    monumentName: "Belur Chennakeshava Temple",
    subtitle: "AI-Powered Multilingual Heritage Assistant",
    tagline: "Explore Hoysala architectural majesty with verified knowledge and spoken responses.",
    askPlaceholder: "Ask about history, architecture, sculptures, or Queen Shantala Devi...",
    askButton: "Send",
    listening: "Listening...",
    processing: "Processing...",
    speaking: "Speaking...",
    groundedBadge: "Verified Source",
    unsupportedNotice: "Answers are grounded exclusively in official heritage archives. Unsupported queries safely fall back without hallucination.",
    citationsTitle: "Verified Document Citations",
    citationPage: "Page",
    relevance: "Relevance",
    attractionsTitle: "Temple Precinct & Highlights",
    exploreMap: "Monuments & Map",
    suggestedTitle: "Curated Inquiries",
    voiceUnavailable: "Microphone unavailable or permission not granted.",
    offlineMode: "Offline First",
    newSession: "New Session",
    clearChat: "Clear History",
    copyAnswer: "Copy answer",
    speakAnswer: "Listen",
    muteAudio: "Audio On",
    unmuteAudio: "Audio Off",
    langEn: "English",
    langKn: "ಕನ್ನಡ",
  },
  kn: {
    siteTitle: "ಸ್ಮಾರ್ಟ್ ಪ್ರವಾಸಿ ಮಾರ್ಗದರ್ಶಿ",
    monumentName: "ಬೇಲೂರು ಶ್ರೀ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ",
    subtitle: "ಕನ್ನಡ-ಇಂಗ್ಲಿಷ್ ದ್ವಿಭಾಷಾ ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ ಸಹಾಯಕ",
    tagline: "ಹೊಯ್ಸಳ ಸಾಮ್ರಾಜ್ಯದ ಶಿಲ್ಪಕಲಾ ವೈಭವ ಮತ್ತು ಇತಿಹಾಸವನ್ನು ಅಧಿಕೃತ ದಾಖಲೆಗಳೊಂದಿಗೆ ಅನ್ವೇಷಿಸಿ.",
    askPlaceholder: "ಇತಿಹಾಸ, ವಾಸ್ತುಶಿಲ್ಪ, ಶಿಲಾಬಾಲಿಕೆಯರು ಅಥವಾ ಶಾಂತಲಾದೇವಿಯ ಕುರಿತು ಕೇಳಿ...",
    askButton: "ಕಳುಹಿಸಿ",
    listening: "ಆಲಿಸುತ್ತಿದೆ...",
    processing: "ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ...",
    speaking: "ಧ್ವನಿ ಪ್ರಸಾರವಾಗುತ್ತಿದೆ...",
    groundedBadge: "ಪರಿಶೀಲಿತ ಆಧಾರ",
    unsupportedNotice: "ಉತ್ತರಗಳು ದೇವಾಲಯದ ಅಧಿಕೃತ ಜ್ಞಾನ ಭಂಡಾರವನ್ನು ಮಾತ್ರ ಆಧರಿಸಿವೆ. ಆಧಾರವಿಲ್ಲದ ಪ್ರಶ್ನೆಗಳಿಗೆ ಕಲ್ಪಿತ ಉತ್ತರಗಳನ್ನು ನೀಡಲಾಗುವುದಿಲ್ಲ.",
    citationsTitle: "ಅಧಿಕೃತ ಆಧಾರ ದಾಖಲೆಗಳು",
    citationPage: "ಪುಟ",
    relevance: "ಹೊಂದಾಣಿಕೆ",
    attractionsTitle: "ದೇವಾಲಯದ ಪ್ರಮುಖ ತಾಣಗಳು",
    exploreMap: "ತಾಣಗಳು & ನಕ್ಷೆ",
    suggestedTitle: "ಪ್ರಮುಖ ಪ್ರಶ್ನೆಗಳು",
    voiceUnavailable: "ಮೈಕ್ರೊಫೋನ್ ಲಭ್ಯವಿಲ್ಲ ಅಥವಾ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ.",
    offlineMode: "ಆಫ್‌ಲೈನ್ ಕಾರ್ಯಾಚರಣೆ",
    newSession: "ಹೊಸ ಸಂಭಾಷಣೆ",
    clearChat: "ಇತಿಹಾಸ ತೆರವು",
    copyAnswer: "ಪ್ರತಿ ಮಾಡಿಕೊಳ್ಳಿ",
    speakAnswer: "ಕೇಳಿ",
    muteAudio: "ಧ್ವನಿ ಸಕ್ರಿಯ",
    unmuteAudio: "ಧ್ವನಿ ನಿಷ್ಕ್ರಿಯ",
    langEn: "English",
    langKn: "ಕನ್ನಡ",
  },
} as const;
