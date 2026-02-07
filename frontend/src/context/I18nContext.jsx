import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { translations, defaultLanguage, getNestedValue, languages, hasStaticTranslation, isRTL, getLanguageInfo } from '../lib/i18n';
import { translateFullTranslationObject } from '../lib/geminiTranslate';
import en from '../lib/i18n/translations/en';

const I18nContext = createContext(null);

const LANGUAGE_STORAGE_KEY = 'sayless_language';
const FIRST_VISIT_KEY = 'sayless_first_visit';
const TRANSLATION_CACHE_KEY = 'sayless_translations_cache';

export function I18nProvider({ children }) {
    const [language, setLanguageState] = useState(defaultLanguage);
    const [isFirstVisit, setIsFirstVisit] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [isTranslating, setIsTranslating] = useState(false);
    const [translationProgress, setTranslationProgress] = useState(0);
    const [dynamicTranslations, setDynamicTranslations] = useState({});
    const translationInProgress = useRef(false);

    // Load cached dynamic translations from localStorage
    useEffect(() => {
        try {
            const cached = localStorage.getItem(TRANSLATION_CACHE_KEY);
            if (cached) {
                setDynamicTranslations(JSON.parse(cached));
            }
        } catch (e) {
            console.error('Error loading translation cache:', e);
        }
    }, []);

    // Initialize language from localStorage
    useEffect(() => {
        const storedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY);
        const hasVisited = localStorage.getItem(FIRST_VISIT_KEY);

        if (storedLanguage) {
            // Check if it's a valid language code
            const isValidLang = languages.some(l => l.code === storedLanguage);
            if (isValidLang) {
                setLanguageState(storedLanguage);
                setIsFirstVisit(false);
            } else if (!hasVisited) {
                setIsFirstVisit(true);
            }
        } else if (!hasVisited) {
            // First visit - show language selection modal
            setIsFirstVisit(true);
        }

        setIsLoading(false);
    }, []);

    // Translate content when language changes to a non-static language
    useEffect(() => {
        async function translateIfNeeded() {
            if (!hasStaticTranslation(language) && !dynamicTranslations[language]) {
                // Check if translation is already in progress
                if (translationInProgress.current) return;

                translationInProgress.current = true;
                setIsTranslating(true);
                setTranslationProgress(0);

                try {
                    const langInfo = getLanguageInfo(language);
                    const translated = await translateFullTranslationObject(
                        en, // Use English as base for translation
                        language,
                        langInfo.name,
                        (progress) => setTranslationProgress(progress)
                    );

                    setDynamicTranslations(prev => {
                        const updated = { ...prev, [language]: translated };
                        // Cache in localStorage (with size limit)
                        try {
                            const cacheString = JSON.stringify(updated);
                            if (cacheString.length < 5000000) { // 5MB limit
                                localStorage.setItem(TRANSLATION_CACHE_KEY, cacheString);
                            }
                        } catch (e) {
                            console.error('Error caching translations:', e);
                        }
                        return updated;
                    });
                } catch (error) {
                    console.error('Translation error:', error);
                } finally {
                    setIsTranslating(false);
                    setTranslationProgress(100);
                    translationInProgress.current = false;
                }
            }
        }

        translateIfNeeded();
    }, [language, dynamicTranslations]);

    // Set language and persist to localStorage
    const setLanguage = useCallback((lang) => {
        // Check if it's a valid language
        const isValidLang = languages.some(l => l.code === lang);
        if (isValidLang) {
            setLanguageState(lang);
            localStorage.setItem(LANGUAGE_STORAGE_KEY, lang);
            localStorage.setItem(FIRST_VISIT_KEY, 'true');
            setIsFirstVisit(false);

            // Set RTL direction if needed
            if (isRTL(lang)) {
                document.documentElement.dir = 'rtl';
            } else {
                document.documentElement.dir = 'ltr';
            }
        }
    }, []);

    // Translation function
    const t = useCallback((key, replacements = {}) => {
        let translation;

        // Check if we have a static translation
        if (hasStaticTranslation(language)) {
            translation = getNestedValue(translations[language], key);
        } else {
            // Use dynamic translation if available
            translation = getNestedValue(dynamicTranslations[language], key);
        }

        if (!translation) {
            // Fallback to English if translation not found
            const fallback = getNestedValue(translations[defaultLanguage], key);
            if (!fallback) {
                console.warn(`Translation not found for key: ${key}`);
                return key;
            }
            return processReplacements(fallback, replacements);
        }

        return processReplacements(translation, replacements);
    }, [language, dynamicTranslations]);

    // Process string replacements like {category}
    const processReplacements = (str, replacements) => {
        if (typeof str !== 'string') return str;

        return Object.entries(replacements).reduce((acc, [key, value]) => {
            return acc.replace(new RegExp(`\\{${key}\\}`, 'g'), value);
        }, str);
    };

    // Close the first visit modal without selecting language (use default)
    const dismissFirstVisit = useCallback(() => {
        localStorage.setItem(FIRST_VISIT_KEY, 'true');
        setIsFirstVisit(false);
    }, []);

    // Get current language info
    const currentLanguageInfo = getLanguageInfo(language);

    // Clear translation cache
    const clearTranslationCache = useCallback(() => {
        localStorage.removeItem(TRANSLATION_CACHE_KEY);
        setDynamicTranslations({});
    }, []);

    const value = {
        language,
        setLanguage,
        t,
        isFirstVisit,
        dismissFirstVisit,
        isLoading,
        isTranslating,
        translationProgress,
        currentLanguageInfo,
        languages,
        isRTL: isRTL(language),
        clearTranslationCache,
    };

    return (
        <I18nContext.Provider value={value}>
            {children}
        </I18nContext.Provider>
    );
}

export function useI18n() {
    const context = useContext(I18nContext);
    if (!context) {
        throw new Error('useI18n must be used within an I18nProvider');
    }
    return context;
}

export default I18nContext;
