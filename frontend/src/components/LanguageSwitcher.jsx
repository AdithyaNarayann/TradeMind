import { useState, useMemo } from 'react';
import { Globe, ChevronDown, Search, Sparkles, Loader2 } from 'lucide-react';
import { useI18n } from '../context/I18nContext';
import { languages } from '../lib/i18n';

export default function LanguageSwitcher() {
    const { language, setLanguage, isTranslating, translationProgress, currentLanguageInfo } = useI18n();
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    const currentLang = currentLanguageInfo || languages[0];

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

    // Group languages: static first, then popular, then others
    const groupedLanguages = useMemo(() => {
        const staticLangs = filteredLanguages.filter(l => l.isStatic);
        const popularCodes = ['es', 'fr', 'de', 'zh', 'ja', 'ko', 'pt', 'ru', 'ar'];
        const popularLangs = filteredLanguages.filter(l => !l.isStatic && popularCodes.includes(l.code));
        const otherLangs = filteredLanguages.filter(l => !l.isStatic && !popularCodes.includes(l.code));
        return { static: staticLangs, popular: popularLangs, other: otherLangs };
    }, [filteredLanguages]);

    const handleSelectLanguage = (langCode) => {
        setLanguage(langCode);
        setIsOpen(false);
        setSearchQuery('');
    };

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-3 py-2 border-[2px] border-neo-navy bg-neo-cream
                   font-bold text-sm uppercase tracking-wide transition-all duration-150
                   hover:bg-neo-orange hover:translate-x-[1px] hover:translate-y-[1px]"
            >
                {isTranslating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                    <Globe className="w-4 h-4" />
                )}
                <span className="hidden sm:inline">{currentLang.flag}</span>
                <span className="hidden md:inline">{currentLang.code.toUpperCase()}</span>
                <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <>
                    {/* Backdrop to close dropdown */}
                    <div
                        className="fixed inset-0 z-40"
                        onClick={() => {
                            setIsOpen(false);
                            setSearchQuery('');
                        }}
                    />

                    {/* Dropdown */}
                    <div className="absolute right-0 top-full mt-2 z-50 border-[3px] border-neo-navy bg-neo-cream shadow-neo w-80 max-h-[70vh] flex flex-col">
                        {/* Search */}
                        <div className="p-2 border-b-[2px] border-neo-navy">
                            <div className="relative">
                                <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-neo-navy/50" />
                                <input
                                    type="text"
                                    placeholder="Search languages..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full pl-8 pr-3 py-2 text-sm border-[2px] border-neo-navy bg-white
                                             focus:outline-none focus:border-neo-teal"
                                    autoFocus
                                />
                            </div>
                        </div>

                        {/* Translation Progress */}
                        {isTranslating && (
                            <div className="p-2 border-b-[2px] border-neo-navy bg-neo-teal/10">
                                <div className="flex items-center gap-2 text-xs text-neo-navy">
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                    <span>Translating... {translationProgress}%</span>
                                </div>
                                <div className="w-full bg-neo-navy/20 h-1 mt-1 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-neo-teal transition-all duration-300"
                                        style={{ width: `${translationProgress}%` }}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Language List */}
                        <div className="flex-1 overflow-y-auto">
                            {/* Static Languages */}
                            {groupedLanguages.static.length > 0 && (
                                <div className="p-2">
                                    <p className="text-xs font-bold uppercase text-neo-navy/50 mb-1 flex items-center gap-1">
                                        <span className="w-1.5 h-1.5 bg-neo-teal"></span>
                                        Instant
                                    </p>
                                    {groupedLanguages.static.map(lang => (
                                        <LanguageOption
                                            key={lang.code}
                                            lang={lang}
                                            isSelected={language === lang.code}
                                            onClick={() => handleSelectLanguage(lang.code)}
                                        />
                                    ))}
                                </div>
                            )}

                            {/* Popular Languages */}
                            {groupedLanguages.popular.length > 0 && (
                                <div className="p-2 border-t-[2px] border-neo-navy/20">
                                    <p className="text-xs font-bold uppercase text-neo-navy/50 mb-1 flex items-center gap-1">
                                        <Sparkles className="w-3 h-3" />
                                        Popular
                                    </p>
                                    {groupedLanguages.popular.map(lang => (
                                        <LanguageOption
                                            key={lang.code}
                                            lang={lang}
                                            isSelected={language === lang.code}
                                            onClick={() => handleSelectLanguage(lang.code)}
                                            showAiBadge
                                        />
                                    ))}
                                </div>
                            )}

                            {/* Other Languages */}
                            {groupedLanguages.other.length > 0 && (
                                <div className="p-2 border-t-[2px] border-neo-navy/20">
                                    <p className="text-xs font-bold uppercase text-neo-navy/50 mb-1 flex items-center gap-1">
                                        <Globe className="w-3 h-3" />
                                        All ({groupedLanguages.other.length})
                                    </p>
                                    {groupedLanguages.other.map(lang => (
                                        <LanguageOption
                                            key={lang.code}
                                            lang={lang}
                                            isSelected={language === lang.code}
                                            onClick={() => handleSelectLanguage(lang.code)}
                                            showAiBadge
                                        />
                                    ))}
                                </div>
                            )}

                            {/* No results */}
                            {filteredLanguages.length === 0 && (
                                <div className="p-4 text-center text-neo-navy/50 text-sm">
                                    No languages found
                                </div>
                            )}
                        </div>

                        {/* Footer hint */}
                        <div className="p-2 border-t-[2px] border-neo-navy bg-neo-navy/5 text-center">
                            <p className="text-xs text-neo-navy/50">
                                🌍 75+ languages • AI-powered translation
                            </p>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}

function LanguageOption({ lang, isSelected, onClick, showAiBadge }) {
    return (
        <button
            onClick={onClick}
            className={`
                w-full px-3 py-2 flex items-center gap-3 text-left transition-colors rounded
                ${isSelected
                    ? 'bg-neo-teal text-neo-cream'
                    : 'hover:bg-neo-orange'
                }
            `}
        >
            <span className="text-lg">{lang.flag}</span>
            <div className="flex-1 min-w-0">
                <p className="font-bold text-sm truncate">{lang.nativeName}</p>
                <p className="text-xs opacity-70 truncate">{lang.name}</p>
            </div>
            {showAiBadge && !isSelected && (
                <span className="text-[10px] bg-neo-teal/20 text-neo-teal px-1 py-0.5 font-bold">
                    AI
                </span>
            )}
            {isSelected && (
                <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                </svg>
            )}
        </button>
    );
}
