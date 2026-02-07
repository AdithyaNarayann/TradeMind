import { Loader2, Sparkles } from 'lucide-react';
import { useI18n } from '../context/I18nContext';

export default function TranslationLoadingOverlay() {
    const { isTranslating, translationProgress, currentLanguageInfo } = useI18n();

    if (!isTranslating) return null;

    return (
        <div className="fixed inset-0 bg-neo-navy/80 backdrop-blur-sm flex items-center justify-center z-[90] transition-opacity">
            <div className="bg-neo-cream border-[4px] border-neo-navy shadow-neo p-8 max-w-md w-full mx-4 text-center">
                {/* Animated icon */}
                <div className="relative w-20 h-20 mx-auto mb-6">
                    <div className="absolute inset-0 bg-neo-teal border-[4px] border-neo-navy animate-pulse">
                        <Sparkles className="w-10 h-10 text-neo-cream absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                    </div>
                    <Loader2 className="w-8 h-8 text-neo-orange absolute -top-2 -right-2 animate-spin" />
                </div>

                {/* Title */}
                <h3 className="font-heading font-bold text-2xl text-neo-navy mb-2">
                    Translating with Gemini AI
                </h3>

                {/* Target language */}
                <p className="text-neo-navy/70 mb-4">
                    Converting to <span className="font-bold text-neo-teal">{currentLanguageInfo?.nativeName}</span>
                    <span className="ml-2">{currentLanguageInfo?.flag}</span>
                </p>

                {/* Progress bar */}
                <div className="w-full bg-neo-navy/20 h-3 border-[2px] border-neo-navy mb-2">
                    <div
                        className="h-full bg-gradient-to-r from-neo-teal to-neo-orange transition-all duration-300 ease-out"
                        style={{ width: `${translationProgress}%` }}
                    />
                </div>

                {/* Progress text */}
                <p className="text-sm text-neo-navy/60">
                    <span className="font-bold text-neo-navy">{translationProgress}%</span> complete
                </p>

                {/* Info text */}
                <p className="text-xs text-neo-navy/50 mt-4">
                    Translations will be cached for instant loading next time
                </p>
            </div>
        </div>
    );
}
