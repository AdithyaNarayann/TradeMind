import en from './translations/en';
import hi from './translations/hi';

// Static translations for English and Hindi
export const translations = {
    en,
    hi,
};

// Languages with static translations (no API calls needed)
export const staticLanguages = ['en', 'hi'];

// Comprehensive list of 50+ languages with flags and native names
// English and Hindi use static translations
// All other languages use Gemini API for live translation
export const languages = [
    // Static translations (English & Hindi)
    { code: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸', isStatic: true },
    { code: 'hi', name: 'Hindi', nativeName: 'हिंदी', flag: '🇮🇳', isStatic: true },

    // ═══════════════════════════════════════════════════════════════════
    // Asian Languages
    // ═══════════════════════════════════════════════════════════════════
    { code: 'zh', name: 'Chinese (Simplified)', nativeName: '简体中文', flag: '🇨🇳', isStatic: false },
    { code: 'zh-TW', name: 'Chinese (Traditional)', nativeName: '繁體中文', flag: '🇹🇼', isStatic: false },
    { code: 'ja', name: 'Japanese', nativeName: '日本語', flag: '🇯🇵', isStatic: false },
    { code: 'ko', name: 'Korean', nativeName: '한국어', flag: '🇰🇷', isStatic: false },
    { code: 'th', name: 'Thai', nativeName: 'ไทย', flag: '🇹🇭', isStatic: false },
    { code: 'vi', name: 'Vietnamese', nativeName: 'Tiếng Việt', flag: '🇻🇳', isStatic: false },
    { code: 'id', name: 'Indonesian', nativeName: 'Bahasa Indonesia', flag: '🇮🇩', isStatic: false },
    { code: 'ms', name: 'Malay', nativeName: 'Bahasa Melayu', flag: '🇲🇾', isStatic: false },
    { code: 'fil', name: 'Filipino', nativeName: 'Filipino', flag: '🇵🇭', isStatic: false },
    { code: 'my', name: 'Burmese', nativeName: 'မြန်မာ', flag: '🇲🇲', isStatic: false },
    { code: 'km', name: 'Khmer', nativeName: 'ខ្មែរ', flag: '🇰🇭', isStatic: false },
    { code: 'lo', name: 'Lao', nativeName: 'ລາວ', flag: '🇱🇦', isStatic: false },
    { code: 'mn', name: 'Mongolian', nativeName: 'Монгол', flag: '🇲🇳', isStatic: false },
    { code: 'ne', name: 'Nepali', nativeName: 'नेपाली', flag: '🇳🇵', isStatic: false },
    { code: 'si', name: 'Sinhala', nativeName: 'සිංහල', flag: '🇱🇰', isStatic: false },
    { code: 'bn', name: 'Bengali', nativeName: 'বাংলা', flag: '🇧🇩', isStatic: false },
    { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்', flag: '🇮🇳', isStatic: false },
    { code: 'te', name: 'Telugu', nativeName: 'తెలుగు', flag: '🇮🇳', isStatic: false },
    { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ', flag: '🇮🇳', isStatic: false },
    { code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം', flag: '🇮🇳', isStatic: false },
    { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી', flag: '🇮🇳', isStatic: false },
    { code: 'mr', name: 'Marathi', nativeName: 'मराठी', flag: '🇮🇳', isStatic: false },
    { code: 'pa', name: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ', flag: '🇮🇳', isStatic: false },
    { code: 'ur', name: 'Urdu', nativeName: 'اردو', flag: '🇵🇰', isStatic: false },

    // ═══════════════════════════════════════════════════════════════════
    // European Languages
    // ═══════════════════════════════════════════════════════════════════
    { code: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸', isStatic: false },
    { code: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷', isStatic: false },
    { code: 'de', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪', isStatic: false },
    { code: 'it', name: 'Italian', nativeName: 'Italiano', flag: '🇮🇹', isStatic: false },
    { code: 'pt', name: 'Portuguese', nativeName: 'Português', flag: '🇵🇹', isStatic: false },
    { code: 'pt-BR', name: 'Portuguese (Brazil)', nativeName: 'Português (Brasil)', flag: '🇧🇷', isStatic: false },
    { code: 'ru', name: 'Russian', nativeName: 'Русский', flag: '🇷🇺', isStatic: false },
    { code: 'uk', name: 'Ukrainian', nativeName: 'Українська', flag: '🇺🇦', isStatic: false },
    { code: 'pl', name: 'Polish', nativeName: 'Polski', flag: '🇵🇱', isStatic: false },
    { code: 'nl', name: 'Dutch', nativeName: 'Nederlands', flag: '🇳🇱', isStatic: false },
    { code: 'sv', name: 'Swedish', nativeName: 'Svenska', flag: '🇸🇪', isStatic: false },
    { code: 'no', name: 'Norwegian', nativeName: 'Norsk', flag: '🇳🇴', isStatic: false },
    { code: 'da', name: 'Danish', nativeName: 'Dansk', flag: '🇩🇰', isStatic: false },
    { code: 'fi', name: 'Finnish', nativeName: 'Suomi', flag: '🇫🇮', isStatic: false },
    { code: 'el', name: 'Greek', nativeName: 'Ελληνικά', flag: '🇬🇷', isStatic: false },
    { code: 'cs', name: 'Czech', nativeName: 'Čeština', flag: '🇨🇿', isStatic: false },
    { code: 'sk', name: 'Slovak', nativeName: 'Slovenčina', flag: '🇸🇰', isStatic: false },
    { code: 'hu', name: 'Hungarian', nativeName: 'Magyar', flag: '🇭🇺', isStatic: false },
    { code: 'ro', name: 'Romanian', nativeName: 'Română', flag: '🇷🇴', isStatic: false },
    { code: 'bg', name: 'Bulgarian', nativeName: 'Български', flag: '🇧🇬', isStatic: false },
    { code: 'hr', name: 'Croatian', nativeName: 'Hrvatski', flag: '🇭🇷', isStatic: false },
    { code: 'sr', name: 'Serbian', nativeName: 'Српски', flag: '🇷🇸', isStatic: false },
    { code: 'sl', name: 'Slovenian', nativeName: 'Slovenščina', flag: '🇸🇮', isStatic: false },
    { code: 'lt', name: 'Lithuanian', nativeName: 'Lietuvių', flag: '🇱🇹', isStatic: false },
    { code: 'lv', name: 'Latvian', nativeName: 'Latviešu', flag: '🇱🇻', isStatic: false },
    { code: 'et', name: 'Estonian', nativeName: 'Eesti', flag: '🇪🇪', isStatic: false },
    { code: 'is', name: 'Icelandic', nativeName: 'Íslenska', flag: '🇮🇸', isStatic: false },
    { code: 'ga', name: 'Irish', nativeName: 'Gaeilge', flag: '🇮🇪', isStatic: false },
    { code: 'cy', name: 'Welsh', nativeName: 'Cymraeg', flag: '🏴󠁧󠁢󠁷󠁬󠁳󠁿', isStatic: false },
    { code: 'ca', name: 'Catalan', nativeName: 'Català', flag: '🇪🇸', isStatic: false },
    { code: 'eu', name: 'Basque', nativeName: 'Euskara', flag: '🇪🇸', isStatic: false },
    { code: 'gl', name: 'Galician', nativeName: 'Galego', flag: '🇪🇸', isStatic: false },

    // ═══════════════════════════════════════════════════════════════════
    // Middle Eastern & African Languages
    // ═══════════════════════════════════════════════════════════════════
    { code: 'ar', name: 'Arabic', nativeName: 'العربية', flag: '🇸🇦', isStatic: false, rtl: true },
    { code: 'he', name: 'Hebrew', nativeName: 'עברית', flag: '🇮🇱', isStatic: false, rtl: true },
    { code: 'fa', name: 'Persian', nativeName: 'فارسی', flag: '🇮🇷', isStatic: false, rtl: true },
    { code: 'tr', name: 'Turkish', nativeName: 'Türkçe', flag: '🇹🇷', isStatic: false },
    { code: 'sw', name: 'Swahili', nativeName: 'Kiswahili', flag: '🇹🇿', isStatic: false },
    { code: 'am', name: 'Amharic', nativeName: 'አማርኛ', flag: '🇪🇹', isStatic: false },
    { code: 'ha', name: 'Hausa', nativeName: 'Hausa', flag: '🇳🇬', isStatic: false },
    { code: 'yo', name: 'Yoruba', nativeName: 'Yorùbá', flag: '🇳🇬', isStatic: false },
    { code: 'ig', name: 'Igbo', nativeName: 'Igbo', flag: '🇳🇬', isStatic: false },
    { code: 'zu', name: 'Zulu', nativeName: 'isiZulu', flag: '🇿🇦', isStatic: false },
    { code: 'af', name: 'Afrikaans', nativeName: 'Afrikaans', flag: '🇿🇦', isStatic: false },

    // ═══════════════════════════════════════════════════════════════════
    // Other Languages
    // ═══════════════════════════════════════════════════════════════════
    { code: 'ka', name: 'Georgian', nativeName: 'ქართული', flag: '🇬🇪', isStatic: false },
    { code: 'hy', name: 'Armenian', nativeName: 'Հայերեն', flag: '🇦🇲', isStatic: false },
    { code: 'az', name: 'Azerbaijani', nativeName: 'Azərbaycan', flag: '🇦🇿', isStatic: false },
    { code: 'kk', name: 'Kazakh', nativeName: 'Қазақ', flag: '🇰🇿', isStatic: false },
    { code: 'uz', name: 'Uzbek', nativeName: "O'zbek", flag: '🇺🇿', isStatic: false },
    { code: 'tg', name: 'Tajik', nativeName: 'Тоҷикӣ', flag: '🇹🇯', isStatic: false },
    { code: 'ky', name: 'Kyrgyz', nativeName: 'Кыргызча', flag: '🇰🇬', isStatic: false },
    { code: 'tk', name: 'Turkmen', nativeName: 'Türkmen', flag: '🇹🇲', isStatic: false },
    { code: 'la', name: 'Latin', nativeName: 'Latina', flag: '🏛️', isStatic: false },
    { code: 'eo', name: 'Esperanto', nativeName: 'Esperanto', flag: '🌍', isStatic: false },
];

export const defaultLanguage = 'en';

// Helper function to get nested translation value
export const getNestedValue = (obj, path) => {
    return path.split('.').reduce((acc, part) => acc && acc[part], obj);
};

// Check if a language uses RTL (Right-to-Left) text direction
export const isRTL = (langCode) => {
    const lang = languages.find(l => l.code === langCode);
    return lang?.rtl || false;
};

// Check if a language has static translations
export const hasStaticTranslation = (langCode) => {
    return staticLanguages.includes(langCode);
};

// Get language info by code
export const getLanguageInfo = (langCode) => {
    return languages.find(l => l.code === langCode) || languages[0];
};
