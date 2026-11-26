"""Cross-lingual query normalization service uniting neural translation, domain glossaries, and intent expansion."""

import re
from backend.src.application.chat.language_detector import LanguageDetector
from backend.src.application.translation.heritage_glossary import HeritageGlossary
from backend.src.application.translation.transliteration import transliterate_kannada_to_latin
from backend.src.core.logging import get_logger
from backend.src.domain.translation import NormalizedQuery, TranslationStrategy
from backend.src.infrastructure.translation.argos_engine import ArgosTranslationEngine, get_argos_engine
from backend.src.infrastructure.translation.nllb_engine import NllbTranslationEngine, get_nllb_engine

logger = get_logger("application.translation.query_normalizer")

# Common Kannada lexical terms translated to English domain equivalents for RAG retrieval
COMMON_KANNADA_TERMS: list[tuple[re.Pattern, str]] = [
    # Precinct Shrines & UNESCO Attractions
    (re.compile(r"(?:ಸೌಮ್ಯನಾಯಕಿ|ಸೋಮನಾಯಕಿ|ಸೋಮ್ಯನಾಯಕಿ)(?:\s*(?:ದೇವಾಲಯ|ಗುಡಿ|ಸನ್ನಿಧಿ|ಅಮ್ಮನವರ))?(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ಯನ್ನು|ಯ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Somanayaki Saumyanayaki Soumyanayaki temple vimana tower"),
    (re.compile(r"(?:ವೀರನಾರಾಯಣ|ವೀರ\s*ನಾರಾಯಣ)(?:\s*(?:ದೇವಾಲಯ|ಗುಡಿ|ಸನ್ನಿಧಿ))?(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ಯನ್ನು|ಯ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Vira Narayana Temple Vira-Narayana compact Hoysala shrine"),
    (re.compile(r"(?:ಆಂಡಾಳ್|ರಂಗನಾಯಕಿ)(?:\s*(?:ದೇವಾಲಯ|ಗುಡಿ|ಸನ್ನಿಧಿ))?(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ಯನ್ನು|ಯ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Andal Temple Ranganayaki female saint shrine"),
    (re.compile(r"(?:ಉತ್ತರ\s*ಮಂಟಪ|ಉತ್ತರದ\s*ಮಂಟಪ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "North Pavilion northern side Vasudeva Sarovara Vijayanagara mandapa"),
    (re.compile(r"(?:ಆಗ್ನೇಯ\s*ಮಂಟಪ|ಆಗ್ನೇಯದ\s*ಮಂಟಪ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "South-Eastern Pavilion ancillary structures flat ceilings Vijayanagara"),
    (re.compile(r"(?:ಪೂರ್ವ\s*ಮಂಟಪ|ಪೂರ್ವದ\s*ಮಂಟಪ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "East Pavilion eastern pavilion Vasudeva Sarovara"),
    (re.compile(r"(?:ಮುಜರಾಯಿ\s*ಕಚೇರಿ|ಮುಜರಾಯಿ\s*ಕಟ್ಟಡ)(?:\s*\(ಐತಿಹಾಸಿಕ\s*ಕಟ್ಟಡ\))?(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ಯನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Muzrai Office Hindu Religious Charitable Endowments Wodeyar"),
    (re.compile(r"(?:ಉಯ್ಯಾಲೆ|ವ್ಯಾಳೆ)\s*ಮಂಟಪ(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Swinging mantapas swing pavilion Vyaule Mandapa"),
    (re.compile(r"(?:ದೀಪಸ್ತಂಭ|ದೀಪ\s*ಸ್ತಂಭ|ಗುರುತ್ವಾಕರ್ಷಣಾ?\s*ಸ್ತಂಭ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Gravity Pillar 42 feet stone pole courtyard weight and balance"),
    (re.compile(r"(?:ವಾಸುದೇವ\s*ಸರೋವರ|ಕಲ್ಯಾಣಿ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ಯನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Vasudeva-sarovara pond Vasudeva stepped water tank"),
    (re.compile(r"(?:ಆನೆ\s*ಬಾಗಿಲು|ಆನೆದ್ವಾರ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Elephant's Gate Elephant Gate royal portrait slab Vishnuvardhana Santale"),
    (re.compile(r"(?:ರಾಯ\s*ಗೋಪುರ|ರಾಜಗೋಪುರ|ಮಹಾದ್ವಾರ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "main gateway gopura gopuram Raya Gopura seven-story"),
    (re.compile(r"(?:ಧಾನ್ಯ\s*ಸಂಗ್ರಹಾಗಾರ|ಕಣಜ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Stone granary King Ballala II grain store"),
    (re.compile(r"(?:ಕಲ್ಯಾಣ\s*ಮಂಟಪ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Kalyana Mandapa ceremonial wedding pavilion"),
    (re.compile(r"(?:ಪ್ರಾಕಾರದ?\s*(?:ಕೋಟೆ\s*)?ಗೋಡೆ|ಸುತ್ತುಗೋಡೆ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ಯನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "walled courtyard walled enclosure perimeter boundary wall"),
    (re.compile(r"(?:ಕಕ್ಷಾಸನ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Kakshasana perimeter stone bench seating lattice screens"),
    (re.compile(r"(?:ಅಂತರಾಳ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Antarala vestibule passage Sala royal emblem"),
    (re.compile(r"(?:ದ್ವಾರ\s*ಮಂಟಪ|ದ್ವಾರಮಂಟಪ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ವನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Dvara Mandapa projecting entrance porches perforated jali screens"),
    # Main hall / navaranga / mandapa (with locative and nominal inflections)
    (re.compile(r"(?:ಮುಖ್ಯ\s*ಸಭಾಂಗಣ|ಮಧ್ಯ\s*ಸಭಾಂಗಣ|ಸಭಾಂಗಣ|ನವರಂಗ|ಮಧ್ಯರಂಗ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ವನ್ನು|ದ|ಕ್ಕೆ|ಗಳಿಂದ|ಗಳು|ಗಳನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "main hall navaranga central hall"),
    (re.compile(r"(?:ಮಂಟಪ|ಮುಖಮಂಟಪ|ಸಭಾಮಂಟಪ|ರಂಗಮಂಟಪ)(?:ದಲ್ಲಿರುವ|ದಲ್ಲಿ|ವನ್ನು|ದ|ಕ್ಕೆ|ಗಳಿಂದ|ಗಳು|ಗಳನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "mandapa hall pavilion"),
    # Polish / shine / lathe-turned
    (re.compile(r"(?:ಹೊಳಪು\s*ನೀಡಿದ|ಹೊಳಪುಳ್ಳ|ಹೊಳಪಿನ|ಹೊಳಪು|ಹೊಳೆಯುವ|ನಯಗೊಳಿಸಿದ|ನಯವಾದ|ನುಣುಪಾದ|ಮೆರುಗು\s*ನೀಡಿದ|ಮೆರುಗು)(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "polished mirror polish lathe turned smooth shine"),
    # Round / circular / cylindrical
    (re.compile(r"(?:ದುಂಡಗಿನ|ದುಂಡನೆಯ|ದುಂಡಾದ|ದುಂಡು|ವರ್ತುಲಾಕಾರದ|ಗೋಳಾಕಾರದ|ಸಿಲಿಂಡರಾಕಾರದ)(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "round circular cylindrical lathe turned"),
    # Pillars / columns / stambha (inflected forms)
    (re.compile(r"(?:ಕಂಬ|ಸ್ತಂಭ|ಪಿಲ್ಲರ್)(?:ಗಳು|ಗಳನ್ನು|ಗಳಿಂದ|ಗಳಿಗೆ|ಗಳ|ದಲ್ಲಿ|ಗಳಲ್ಲಿ|ವನ್ನು|ದ|ಕ್ಕೆ|ನಿಂದ|ಗೆ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "pillars columns"),
    # How made / crafted / technique
    (re.compile(r"(?:ಹೇಗೆ\s*ಮಾಡಲಾಗಿದೆ|ಹೇಗೆ\s*ಮಾಡಲಾಯಿತು|ಹೇಗೆ\s*ಮಾಡಿದರು|ಹೇಗೆ\s*ತಯಾರಿಸಲಾಗಿದೆ|ಹೇಗೆ\s*ತಯಾರಿಸಲಾಯಿತು|ಹೇಗೆ\s*ತಯಾರಿಸಿದರು|ಹೇಗೆ\s*ನಿರ್ಮಿಸಲಾಗಿದೆ|ಮಾಡಿದ\s*ವಿಧಾನ|ತಯಾರಿಸಿದ\s*ವಿಧಾನ|ಕೆತ್ತಿದ\s*ವಿಧಾನ|ರೂಪಿಸಿದ\s*ವಿಧಾನ)(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "how made crafted constructed technique method lathe turned"),
    # Temple / shrine / sanctuary
    (re.compile(r"(?:ದೇವಾಲಯ|ದೇವಸ್ಥಾನ|ಗುಡಿ|ಕೋವಿಲ್|ಮಂದಿರ)(?:ವನ್ನು|ದಲ್ಲಿ|ದ|ಕ್ಕೆ|ಯನ್ನು|ಗಳಿಂದ|ಗಳು|ಗಳನ್ನು|ಗಳ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "temple shrine sanctuary"),
    # Palace / fort
    (re.compile(r"(?:ಅರಮನೆ|ಕೋಟೆ)(?:ಯನ್ನು|ಯಲ್ಲಿ|ಯ|ಗೆ|ಗಳು|ಗಳನ್ನು)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "palace fort"),
    # Royal patrons & rulers
    (re.compile(r"(?:ರಾಜ|ಮಹಾರಾಜ|ದೊರೆ|ಚಕ್ರವರ್ತಿ)(?:ಯನ್ನು|ಯಿಂದ|ದ|ಗೆ|ಗಳು|ಗಳನ್ನು|ಗಳ|ನು|ನ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "king ruler monarch patron"),
    (re.compile(r"(?:ರಾಣಿ|ಮಹಾರಾಣಿ)(?:ಯನ್ನು|ಯಿಂದ|ಯ|ಗೆ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "queen"),
    # Sculptor & architect
    (re.compile(r"(?:ಶಿಲ್ಪಿ|ಶಿಲ್ಪಿಗಳು|ಶಿಲ್ಪಿಗಳ|ರೂವಾರಿ|ರೂವಾರಿಗಳು|ವಾಸ್ತುಶಿಲ್ಪಿ)(?:ಯನ್ನು|ಯಿಂದ|ದ|ಗೆ|ಗಳು|ಗಳನ್ನು|ಗಳ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "sculptor architect master craftsman"),
    # Carvings / sculptures
    (re.compile(r"(?:ಕೆತ್ತನೆ|ಕೆತ್ತನೆಗಳು|ಶಿಲ್ಪ|ಶಿಲ್ಪಗಳು|ಶಿಲ್ಪಕಲೆ|ವಿಗ್ರಹ|ವಿಗ್ರಹಗಳು|ಮೂರ್ತಿ|ಮೂರ್ತಿಗಳು)(?:ಗಳನ್ನು|ಗಳಿಂದ|ಗಳಿಗೆ|ಗಳ|ದಲ್ಲಿ|ಗಳಲ್ಲಿ|ವನ್ನು|ದ|ಕ್ಕೆ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "carvings sculptures statues relief figures bracket figures"),
    # Madanika / bracket figures
    (re.compile(r"(?:ಮದನಿಕೆ|ಮದನಿಕೆಯರು|ಮದನಿಕಾ|ಶಿಲಾಬಾಲಿಕೆ|ಶಿಲಾಬಾಲಿಕೆಯರು)(?:ಗಳನ್ನು|ಗಳಿಂದ|ಗಳಿಗೆ|ಗಳ|ಯರ|ಯರನ್ನು|ಯರಿಗೆ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "Madanika bracket figures dancing maidens"),
    # Stone / Material
    (re.compile(r"(?:ಕಲ್ಲು|ಕಲ್ಲಿನಿಂದ|ಕಲ್ಲಿನ|ಕಲ್ಲನ್ನು|ಗಲ್ಲು|ಶಿಲೆ|ಶಿಲೆಯಿಂದ|ಬಳಪದ\s*ಕಲ್ಲು|ಸೋಪ್\s*ಸ್ಟೋನ್|ಸಾಮಗ್ರಿ|ವಸ್ತು)(?:ವನ್ನು|ಯಿಂದ|ಯನ್ನು|ದ|ಕ್ಕೆ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "stone material soapstone chloritic schist"),
    # Construction verbs
    (re.compile(r"(?:ಕಟ್ಟಲಾಗಿದೆ|ಕಟ್ಟಲಾಯಿತು|ನಿರ್ಮಿಸಲಾಗಿದೆ|ನಿರ್ಮಿಸಲಾಯಿತು|ಕಟ್ಟಿದ|ಕಟ್ಟಿಸಿದ|ನಿರ್ಮಿಸಿದ)(?:ನು|ರು|ದ್ದಾರೆ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "built constructed commissioned erected"),
    # Quantity / count
    (re.compile(r"(?:ಎಷ್ಟು|ಎಷ್ಟಿವೆ|ಸಂಖ್ಯೆ|ಒಟ್ಟು\s*ಸಂಖ್ಯೆ|ಒಟ್ಟು)(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "how many count total number figures"),
    # Spatial locations
    (re.compile(r"(?:ಹೊರ|ಹೊರಭಾಗ|ಹೊರಗಡೆ|ಹೊರಗೋಡೆ)(?:ಯಲ್ಲಿ|ಯನ್ನು|ಯ|ದ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "exterior outer wall outside"),
    (re.compile(r"(?:ಒಳ|ಒಳಭಾಗ|ಒಳಗಡೆ|ಒಳಾಂಗಣ|ಒಳಗೆ)(?:ಯಲ್ಲಿ|ಯನ್ನು|ಯ|ದ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "interior inner hall inside"),
    # Ceiling / Dome
    (re.compile(r"(?:ಛಾವಣಿ|ಮೇಲ್ಛಾವಣಿ|ಭುವನೇಶ್ವರಿ)(?:ಯಲ್ಲಿ|ಯನ್ನು|ಯ|ಗೆ|ದ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "ceiling central domed ceiling"),
    # Gateway / Entrance
    (re.compile(r"(?:ಪ್ರವೇಶದ್ವಾರ|ದ್ವಾರ|ಬಾಗಿಲು|ಗೋಪುರ|ರಾಜಗೋಪುರ)(?:ದಲ್ಲಿ|ವನ್ನು|ದ|ಕ್ಕೆ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "entrance gateway gopuram doorway"),
    # Inquiries
    (re.compile(r"(?:ವಿವರವಾಗಿ|ವಿವರವಾದ|ವಿವರ|ಮಾಹಿತಿ)(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "in detail details information"),
    (re.compile(r"(?:ಬಗ್ಗೆ|ಕುರಿತು)(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "about details"),
    (re.compile(r"(?:ತಿಳಿಸಿ|ಹೇಳಿ|ವಿವರಿಸಿ)(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "explain describe information"),
    # Year / Century
    (re.compile(r"(?:ವರ್ಷ|ಶತಮಾನ)(?:ದಲ್ಲಿ|ದ|ಕ್ಕೆ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "year century date period"),
    # Location
    (re.compile(r"(?:ಸ್ಥಳ|ಜಿಲ್ಲೆ)(?:ದಲ್ಲಿ|ಯನ್ನು|ಯ|ದ)?(?![ಅ-ಹ\u0c80-\u0cff])", re.IGNORECASE), "place location district route"),
]

KANNADA_UNICODE_PATTERN = re.compile(r"[\u0c80-\u0cff]")

KANNADA_STOPWORDS: set[str] = {
    "ಈ", "ಆ", "ಮತ್ತು", "ಹಾಗೂ", "ಅಥವಾ", "ಇದೆ", "ಇವೆ", "ಇರುವ", "ಆದ",
    "ಆಗಿ", "ಎಂದು", "ಬಗ್ಗೆ", "ಕುರಿತು", "ಒಂದು", "ರಲ್ಲಿ", "ನಲ್ಲಿ", "ದಲ್ಲಿ", "ಯಲ್ಲಿ", "ಅಲ್ಲಿ", "ಇಲ್ಲಿ",
    "ಅದನ್ನು", "ಇದನ್ನು", "ಅದರ", "ಇದರ", "ಅವರು", "ಇವರು", "ಮಾತ್ರ", "ಕೂಡ", "ಸಹ",
}

RETRIEVAL_NOISE_WORDS: set[str] = {
    "about", "details", "detail", "explain", "describe", "information",
    "give", "tell", "me", "please", "more", "a", "an", "the", "in", "of",
    "and", "to", "for", "with", "is", "are", "was", "were", "this", "that",
    "what", "know", "how", "do", "you", "sanctuary", "feet",
    "jehovah", "church", "bible", "mosque", "part", "city",
}


class QueryNormalizer:
    """Normalizes multilingual tourist queries for dense and sparse retrieval while preserving original context."""

    def __init__(
        self,
        nllb_engine: NllbTranslationEngine | None = None,
        argos_engine: ArgosTranslationEngine | None = None,
        glossary: HeritageGlossary | None = None,
        language_detector: LanguageDetector | None = None,
    ) -> None:
        if nllb_engine is None and argos_engine is not None:
            self.nllb_engine = None
        else:
            self.nllb_engine = nllb_engine or get_nllb_engine()
        self.argos_engine = argos_engine or get_argos_engine()
        self.glossary = glossary or HeritageGlossary()
        self.language_detector = language_detector or LanguageDetector()
        self._norm_cache: dict[tuple[str, str, str], NormalizedQuery] = {}

    def normalize_for_retrieval(
        self,
        query: str,
        source_lang: str | None = None,
        target_lang: str = "en",
    ) -> NormalizedQuery:
        """Translate or expand a non-English query into an optimal English retrieval query."""
        clean_query = query.strip()
        if not clean_query:
            return NormalizedQuery(
                original_query=query,
                retrieval_query="",
                detected_language="en",
                preserved_terms=[],
                translation_applied=False,
                strategy_used=TranslationStrategy.PASSTHROUGH,
            )

        # 1. Detect language if not explicitly provided
        has_kannada_script = bool(KANNADA_UNICODE_PATTERN.search(clean_query))
        det_lang = source_lang or ("kn" if has_kannada_script else "en")

        cache_key = (clean_query, det_lang, target_lang)
        if cache_key in self._norm_cache:
            return self._norm_cache[cache_key]

        # 2. English passthrough optimization: if purely English, return immediately with zero overhead
        if not has_kannada_script and det_lang == "en":
            return NormalizedQuery(
                original_query=query,
                retrieval_query=clean_query,
                detected_language="en",
                preserved_terms=[],
                translation_applied=False,
                strategy_used=TranslationStrategy.PASSTHROUGH,
            )

        # 3. Identify and preserve heritage entities (e.g. Belur, Vishnuvardhana, Madanika)
        matched_heritage = self.glossary.extract_heritage_terms(clean_query)
        preserved_terms = list(dict.fromkeys([eng for _, eng in matched_heritage]))

        # 4. Neural translation via NLLB-200 (CTranslate2 INT8)
        if self.nllb_engine and self.nllb_engine.is_available():
            try:
                translated = self.nllb_engine.translate(clean_query, det_lang, target_lang)
                if translated:
                    clean_trans = re.sub(r"\b(?:Beirut|Baylor|Beelor)\b", "Belur", translated, flags=re.IGNORECASE)
                    clean_trans = re.sub(r"\bChennaikeshava\b", "Chennakeshava", clean_trans, flags=re.IGNORECASE)
                    if "Chennakeshava" in preserved_terms:
                        clean_trans = re.sub(r"\bChennai\b", "Chennakeshava", clean_trans, flags=re.IGNORECASE)
                    clean_trans = re.sub(r"\bMadhanika\b", "Madanika", clean_trans, flags=re.IGNORECASE)
                    clean_trans = re.sub(r"\bShanthala\b", "Shantala", clean_trans, flags=re.IGNORECASE)
                    clean_trans = re.sub(r"\bDharpana(?:\s+Sundery)?\b", "Darpana Sundari", clean_trans, flags=re.IGNORECASE)

                    # Reject out-of-domain biblical/religious hallucinations
                    if any(bad in clean_trans.lower() for bad in ["jehovah", "church", "bible", "mosque"]):
                        raise ValueError(f"NLLB hallucinated religious terms in {clean_trans}")

                    # Validation: If query contains known heritage entities, ensure translation did not hallucinate them away
                    if preserved_terms:
                        has_entity = any(
                            term.lower() in clean_trans.lower()
                            or any(w.lower() in clean_trans.lower() for w in term.split() if len(w) > 3)
                            for term in preserved_terms
                        )
                        if not has_entity:
                            logger.warning(
                                "nllb_dropped_heritage_entity_fallback",
                                query=clean_query,
                                translated=clean_trans,
                                preserved=preserved_terms,
                            )
                            # Fall through to domain glossary deterministic translation
                            raise ValueError(f"NLLB dropped preserved entities {preserved_terms}")

                    # Selective expansion: Only append missing architectural or technical terms if not already present
                    words_in_trans = set(re.findall(r"\w+", clean_trans.lower()))
                    extra_terms: list[str] = []

                    # Always ensure authoritative preserved heritage terms are included in retrieval query
                    for term in preserved_terms:
                        for part in term.split():
                            if len(part) > 3 and part.lower() not in words_in_trans and part not in extra_terms:
                                extra_terms.append(part)

                    # Only add intent expansions if the query translation is very short (< 4 words)
                    if len(clean_trans.split()) < 4:
                        expansions = self.glossary.get_intent_expansion(clean_query)
                        for exp in expansions:
                            for term in exp.split():
                                if term.lower() not in words_in_trans and term not in extra_terms:
                                    extra_terms.append(term)

                    # Only append terms if the concept is completely missing from the translation
                    for pat, replacement in COMMON_KANNADA_TERMS:
                        if pat.search(clean_query):
                            rep_words = replacement.split()
                            # If translation already expresses this concept, do not dilute with synonyms
                            concept_present = any(rw.lower() in words_in_trans for rw in rep_words)
                            if not concept_present:
                                for term in rep_words:
                                    if term.lower() not in words_in_trans and term not in extra_terms:
                                        extra_terms.append(term)

                    if preserved_terms:
                        # Prioritize canonical heritage terms first
                        entity_tokens: list[str] = []
                        for term in preserved_terms:
                            for part in term.split():
                                if part.lower() not in [t.lower() for t in entity_tokens]:
                                    entity_tokens.append(part)

                        # Include domain expansion terms from COMMON_KANNADA_TERMS for accurate hybrid matching
                        for pat, replacement in COMMON_KANNADA_TERMS:
                            if pat.search(clean_query):
                                for rw in replacement.split():
                                    if rw.lower() not in [t.lower() for t in entity_tokens]:
                                        entity_tokens.append(rw)

                        # Extract meaningful intent/detail words from translation avoiding noise
                        extra_tokens: list[str] = []
                        for w in re.findall(r"\w+", clean_trans):
                            if (
                                w.lower() not in RETRIEVAL_NOISE_WORDS
                                and w.lower() not in [t.lower() for t in entity_tokens]
                                and w.lower() not in [t.lower() for t in extra_tokens]
                            ):
                                extra_tokens.append(w)

                        final_query = f"{' '.join(entity_tokens)} {' '.join(extra_tokens)}".strip()
                    else:
                        final_query = f"{clean_trans} {' '.join(extra_terms)}".strip() if extra_terms else clean_trans.strip()
                    logger.info(
                        "query_normalized_nllb_neural",
                        original=clean_query,
                        retrieval_query=final_query,
                        preserved=preserved_terms,
                    )
                    res = NormalizedQuery(
                        original_query=query,
                        retrieval_query=final_query,
                        detected_language=det_lang,
                        preserved_terms=preserved_terms,
                        translation_applied=True,
                        strategy_used=TranslationStrategy.ARGOS_NEURAL,
                    )
                    if len(self._norm_cache) >= 1024:
                        self._norm_cache.pop(next(iter(self._norm_cache)))
                    self._norm_cache[cache_key] = res
                    return res
            except Exception as e:
                logger.warning("nllb_query_normalization_fallback", error=str(e))

        # 5. Attempt neural translation via Argos Translate if installed and available
        if self.argos_engine.is_language_pair_available(det_lang, target_lang):
            masked_text, masks = self.glossary.mask_heritage_terms(clean_query)
            translated = self.argos_engine.translate(masked_text, det_lang, target_lang)
            if translated:
                unmasked = self.glossary.unmask_heritage_terms(translated, masks)
                logger.info(
                    "query_normalized_argos_neural",
                    original=clean_query,
                    retrieval_query=unmasked,
                    preserved=preserved_terms,
                )
                return NormalizedQuery(
                    original_query=query,
                    retrieval_query=unmasked.strip(),
                    detected_language=det_lang,
                    preserved_terms=preserved_terms,
                    translation_applied=True,
                    strategy_used=TranslationStrategy.ARGOS_NEURAL,
                )

        # 6. Deterministic Domain Translation & Intent Expansion Strategy
        # Used when neural model package is unavailable offline or fails
        query_working = clean_query

        # A. Replace matched heritage terms with canonical English representations
        for kn_term, en_term in matched_heritage:
            query_working = query_working.replace(kn_term, f" {en_term} ")

        # B. Match question intent patterns (who built, when, where, architecture, ticket, etc.)
        intents = self.glossary.get_intent_expansion(clean_query)

        # C. Translate common architectural and inquiry terms
        for pat, replacement in COMMON_KANNADA_TERMS:
            query_working = pat.sub(f" {replacement} ", query_working)

        # D. Clean extra spaces and assemble retrieval query
        transliterated = transliterate_kannada_to_latin(clean_query)
        retrieval_tokens: list[str] = []

        # Process words from query_working
        raw_words = [w for w in re.split(r"\s+", query_working) if w]
        for w in raw_words:
            if KANNADA_UNICODE_PATTERN.search(w):
                # Skip common Kannada grammatical particles and stop words
                if w in KANNADA_STOPWORDS:
                    continue
                # Unmapped Kannada words (e.g. unknown proper nouns or out-of-domain terms) are transliterated
                latin_w = transliterate_kannada_to_latin(w)
                clean_latin = re.sub(r"[^\w]", "", latin_w).strip()
                if clean_latin and clean_latin.lower() not in [t.lower() for t in retrieval_tokens]:
                    retrieval_tokens.append(clean_latin)
            else:
                clean_eng = re.sub(r"[^\w\-]", "", w).strip()
                if clean_eng:
                    if preserved_terms and clean_eng.lower() in RETRIEVAL_NOISE_WORDS:
                        continue
                    if clean_eng.lower() not in [t.lower() for t in retrieval_tokens]:
                        retrieval_tokens.append(clean_eng)

        # Add intent expansions (e.g. 'who built commissioned constructed', 'history historical background')
        if intents:
            for it in intents:
                for token in it.split():
                    if preserved_terms and token.lower() in RETRIEVAL_NOISE_WORDS:
                        continue
                    if token.lower() not in [t.lower() for t in retrieval_tokens]:
                        retrieval_tokens.append(token)

        if not retrieval_tokens:
            retrieval_tokens.append(transliterated)

        retrieval_query = " ".join(retrieval_tokens).strip()

        logger.info(
            "query_normalized_domain_expansion",
            original=clean_query,
            retrieval_query=retrieval_query,
            preserved=preserved_terms,
        )

        return NormalizedQuery(
            original_query=query,
            retrieval_query=retrieval_query,
            detected_language=det_lang,
            preserved_terms=preserved_terms,
            translation_applied=True,
            strategy_used=TranslationStrategy.DOMAIN_GLOSSARY_EXPANSION,
            transliterated_query=transliterated,
        )
