import { useState, useMemo } from 'react';
import { Globe, Search, Sparkles, Loader2 } from 'lucide-react';
import { useI18n } from '../context/I18nContext';
import { languages } from '../lib/i18n';
import NeoCard from './NeoCard';
import NeoButton from './NeoButton';

export default function LanguageModal() {
    const { isFirstVisit, setLanguage, language, isTranslating, translationProgress } = useI18n();
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedLang, setSelectedLang] = useState(language);

    // Filter languages based on search query
    const filteredLanguages = useMemo(() => {
        if (!searchQuery.trim()) return languages;
        const query = searchQuery.toLowerCase();
        return languages.filter(lang =>
            lang.name.toLowerCase().includes(query) ||
            lang.nativeName.toLowerCase().includes(query) ||
            lang.code.toLowerCase().includes(query)
        );
    }, [searchQuery]);

    // Group languages by category
    const groupedLanguages = useMemo(() => {
        const groups = {
            static: filteredLanguages.filter(l => l.isStatic),
            popular: filteredLanguages.filter(l => !l.isStatic && ['es', 'fr', 'de', 'zh', 'ja', 'ko', 'pt', 'ru', 'ar'].includes(l.code)),
            indian: filteredLanguages.filter(l => !l.isStatic && ['bn', 'ta', 'te', 'kn', 'ml', 'gu', 'mr', 'pa', 'ur', 'ne'].includes(l.code)),
            other: filteredLanguages.filter(l =>
                !l.isStatic &&
                !['es', 'fr', 'de', 'zh', 'ja', 'ko', 'pt', 'ru', 'ar'].includes(l.code) &&
                !['bn', 'ta', 'te', 'kn', 'ml', 'gu', 'mr', 'pa', 'ur', 'ne'].includes(l.code)
            )
        };
        return groups;
    }, [filteredLanguages]);

    if (!isFirstVisit) return null;

    const handleSelectLanguage = (langCode) => {
        setSelectedLang(langCode);
    };

    const handleContinue = () => {
        setLanguage(selectedLang);
    };

    const selectedLangInfo = languages.find(l => l.code === selectedLang);

    return (
        <div className="fixed inset-0 bg-neo-navy/95 flex items-center justify-center p-4 z-[100] overflow-hidden">
            <NeoCard className="max-w-2xl w-full max-h-[90vh] flex flex-col animate-fade-in">
                {/* Header */}
                <div className="text-center p-6 pb-4 border-b-[3px] border-neo-navy">
                    <div className="w-16 h-16 bg-neo-orange border-[4px] border-neo-navy flex items-center justify-center mx-auto mb-4">
                        <Globe className="w-8 h-8 text-neo-navy" />
                    </div>
                    <h2 className="text-2xl font-heading font-bold text-neo-navy mb-1">
                        Choose Your Language
                    </h2>
                    <p className="text-xl font-heading font-bold text-neo-teal mb-1">
                        अपनी भाषा चुनें
                    </p>
                    <p className="text-neo-navy/60 text-sm">
                        Select from 75+ languages • Non-English/Hindi translated live by AI
                    </p>
                </div>

                {/* Search Bar */}
                <div className="p-4 border-b-[3px] border-neo-navy">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neo-navy/50" />
                        <input
                            type="text"
                            placeholder="Search languages..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-3 border-[3px] border-neo-navy bg-neo-cream 
                                     font-heading focus:outline-none focus:bg-white text-neo-navy"
                        />
                    </div>
                </div>

                {/* Language List */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {/* Static Languages (English & Hindi) */}
                    {groupedLanguages.static.length > 0 && (
                        <div>
                            <h3 className="text-xs font-bold uppercase tracking-wider text-neo-navy/50 mb-2 flex items-center gap-2">
                                <span className="w-2 h-2 bg-neo-teal"></span>
                                Recommended (Instant)
                            </h3>
                            <div className="grid grid-cols-2 gap-2">
                                {groupedLanguages.static.map(lang => (
                                    <LanguageButton
                                        key={lang.code}
                                        lang={lang}
                                        isSelected={selectedLang === lang.code}
                                        onClick={() => handleSelectLanguage(lang.code)}
                                        showBadge={false}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Popular Languages */}
                    {groupedLanguages.popular.length > 0 && (
                        <div>
                            <h3 className="text-xs font-bold uppercase tracking-wider text-neo-navy/50 mb-2 flex items-center gap-2">
                                <Sparkles className="w-3 h-3" />
                                Popular (AI Translated)
                            </h3>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                {groupedLanguages.popular.map(lang => (
                                    <LanguageButton
                                        key={lang.code}
                                        lang={lang}
                                        isSelected={selectedLang === lang.code}
                                        onClick={() => handleSelectLanguage(lang.code)}
                                        showBadge={true}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Indian Languages */}
                    {groupedLanguages.indian.length > 0 && (
                        <div>
                            <h3 className="text-xs font-bold uppercase tracking-wider text-neo-navy/50 mb-2 flex items-center gap-2">
                                <span>🇮🇳</span>
                                Indian Languages (AI Translated)
                            </h3>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                {groupedLanguages.indian.map(lang => (
                                    <LanguageButton
                                        key={lang.code}
                                        lang={lang}
                                        isSelected={selectedLang === lang.code}
                                        onClick={() => handleSelectLanguage(lang.code)}
                                        showBadge={true}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Other Languages */}
                    {groupedLanguages.other.length > 0 && (
                        <div>
                            <h3 className="text-xs font-bold uppercase tracking-wider text-neo-navy/50 mb-2 flex items-center gap-2">
                                <Globe className="w-3 h-3" />
                                All Languages (AI Translated)
                            </h3>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                {groupedLanguages.other.map(lang => (
                                    <LanguageButton
                                        key={lang.code}
                                        lang={lang}
                                        isSelected={selectedLang === lang.code}
                                        onClick={() => handleSelectLanguage(lang.code)}
                                        showBadge={true}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* No results */}
                    {filteredLanguages.length === 0 && (
                        <div className="text-center py-8 text-neo-navy/50">
                            <p>No languages found for "{searchQuery}"</p>
                        </div>
                    )}
                </div>

                {/* Footer with Continue Button */}
                <div className="p-4 border-t-[3px] border-neo-navy bg-neo-cream/50">
                    {isTranslating ? (
                        <div className="space-y-2">
                            <div className="flex items-center justify-center gap-2 text-neo-navy">
                                <Loader2 className="w-5 h-5 animate-spin" />
                                <span className="font-bold">Translating with Gemini AI...</span>
                            </div>
                            <div className="w-full bg-neo-navy/20 h-2 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-neo-teal transition-all duration-300"
                                    style={{ width: `${translationProgress}%` }}
                                />
                            </div>
                            <p className="text-xs text-center text-neo-navy/50">
                                {translationProgress}% complete • This will be cached for future visits
                            </p>
                        </div>
                    ) : (
                        <>
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-2">
                                    <span className="text-2xl">{selectedLangInfo?.flag}</span>
                                    <div>
                                        <p className="font-bold text-neo-navy">{selectedLangInfo?.nativeName}</p>
                                        <p className="text-xs text-neo-navy/60">{selectedLangInfo?.name}</p>
                                    </div>
                                </div>
                                {!selectedLangInfo?.isStatic && (
                                    <span className="text-xs bg-neo-teal/20 text-neo-teal px-2 py-1 font-bold">
                                        AI Translated
                                    </span>
                                )}
                            </div>
                            <NeoButton
                                variant="orange"
                                size="lg"
                                className="w-full"
                                onClick={handleContinue}
                            >
                                Continue in {selectedLangInfo?.name} →
                            </NeoButton>
                            <p className="text-center text-xs text-neo-navy/50 mt-2">
                                You can change language anytime from the navbar
                            </p>
                        </>
                    )}
                </div>
            </NeoCard>
        </div>
    );
}

function LanguageButton({ lang, isSelected, onClick, showBadge }) {
    return (
        <button
            onClick={onClick}
            className={`
                p-3 border-[3px] border-neo-navy flex items-center gap-2
                transition-all duration-150 text-left
                hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none
                ${isSelected
                    ? 'bg-neo-orange shadow-none translate-x-[2px] translate-y-[2px]'
                    : 'bg-neo-cream shadow-neo-sm hover:bg-neo-teal hover:text-neo-cream'
                }
            `}
        >
            <span className="text-xl flex-shrink-0">{lang.flag}</span>
            <div className="flex-1 min-w-0">
                <p className="font-bold text-sm truncate">{lang.nativeName}</p>
                <p className="text-xs opacity-70 truncate">{lang.name}</p>
            </div>
            {isSelected && (
                <div className="w-5 h-5 bg-neo-navy flex items-center justify-center flex-shrink-0">
                    <svg className="w-3 h-3 text-neo-cream" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                    </svg>
                </div>
            )}
        </button>
    );
}
