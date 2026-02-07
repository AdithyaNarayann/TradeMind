import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Radio, ArrowLeft, Send, RotateCcw, HelpCircle, Shield, Fingerprint, AlertTriangle } from 'lucide-react';
import Layout from '../components/Layout';
import NeoCard from '../components/NeoCard';
import NeoButton from '../components/NeoButton';
import { useI18n } from '../context/I18nContext';
import { useSession } from '../context/SessionContext';

export default function SilentReport() {
  const { t } = useI18n();

  // Morse-like patterns for categories
  const patterns = {
    'theft': { code: '• •', label: t('silentReport.patterns.theft'), taps: 2 },
    'assault': { code: '• • •', label: t('silentReport.patterns.assault'), taps: 3 },
    'fraud': { code: '• — •', label: t('silentReport.patterns.fraud'), taps: 3 },
    'harassment': { code: '• • • •', label: t('silentReport.patterns.harassment'), taps: 4 },
    'emergency': { code: '— — —', label: t('silentReport.patterns.emergency'), taps: 3 },
  };

  // Severity patterns (number of long taps)
  const severityPatterns = {
    low: { code: '—', level: 1 - 3 },
    medium: { code: '— —', level: 4 - 6 },
    high: { code: '— — —', level: 7 - 10 },
  };

  const { sessionId, walletAddress } = useSession();
  const [taps, setTaps] = useState([]);
  const [holding, setHolding] = useState(false);
  const [holdStart, setHoldStart] = useState(0);
  const [decodedCategory, setDecodedCategory] = useState(null);
  const [decodedSeverity, setDecodedSeverity] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [showInstructions, setShowInstructions] = useState(true);

  // Decode pattern on tap changes
  useEffect(() => {
    if (taps.length === 0) {
      setDecodedCategory(null);
      setDecodedSeverity(null);
      return;
    }

    const shortTaps = taps.filter(t => t === 'short').length;
    const longTaps = taps.filter(t => t === 'long').length;

    // Match category by short tap count
    if (shortTaps === 2 && longTaps === 0) setDecodedCategory('theft');
    else if (shortTaps === 3 && longTaps === 0) setDecodedCategory('assault');
    else if (shortTaps === 2 && longTaps === 1) setDecodedCategory('fraud');
    else if (shortTaps === 4) setDecodedCategory('harassment');
    else if (longTaps >= 3 && shortTaps === 0) setDecodedCategory('emergency');
    else setDecodedCategory(null);

    // Match severity by long tap count
    if (longTaps === 1) setDecodedSeverity('low');
    else if (longTaps === 2) setDecodedSeverity('medium');
    else if (longTaps >= 3) setDecodedSeverity('high');
    else setDecodedSeverity(null);
  }, [taps]);

  const handleTapStart = useCallback(() => {
    setHolding(true);
    setHoldStart(Date.now());
  }, []);

  const handleTapEnd = useCallback(() => {
    if (!holding) return;

    const duration = Date.now() - holdStart;
    const tapType = duration > 500 ? 'long' : 'short';

    setTaps(prev => [...prev, tapType]);
    setHolding(false);
    setHoldStart(0);
  }, [holding, holdStart]);

  const resetTaps = () => {
    setTaps([]);
    setDecodedCategory(null);
    setDecodedSeverity(null);
  };

  const handleSubmit = () => {
    if (decodedCategory) {
      setSubmitted(true);
    }
  };

  if (submitted) {
    return (
      <Layout>
        <div className="min-h-[80vh] flex items-center justify-center p-4 bg-neo-navy">
          <NeoCard variant="teal" className="p-6 sm:p-8 text-center max-w-md w-full">
            <div className="w-16 h-16 sm:w-20 sm:h-20 bg-neo-navy border-[3px] border-neo-navy flex items-center justify-center mx-auto mb-4 sm:mb-6">
              <Radio className="w-8 h-8 sm:w-10 sm:h-10 text-neo-teal" />
            </div>
            <h2 className="text-2xl sm:text-3xl font-heading font-bold mb-2 text-neo-cream">{t('silentReport.silentReportSent')}</h2>
            <p className="text-neo-cream/80 mb-4 text-sm sm:text-base">
              {t('silentReport.transmitted', { category: patterns[decodedCategory]?.label || 'report' })}
            </p>
            <div className="inline-flex items-center gap-2 bg-neo-navy text-neo-cream px-3 py-2 border-[2px] border-neo-navy font-mono text-sm mb-6">
              <Fingerprint className="w-4 h-4" />
              {taps.map(t => t === 'short' ? '•' : '—').join(' ')}
            </div>
            <Link to="/reporter">
              <NeoButton variant="orange" className="w-full">{t('report.backToDashboardBtn')}</NeoButton>
            </Link>
          </NeoCard>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Hero Header */}
      <section className="bg-neo-navy py-6 sm:py-10 border-b-[4px] border-neo-navy">
        <div className="container mx-auto px-4">
          <div className="max-w-2xl mx-auto">
            <Link to="/reporter" className="inline-flex items-center gap-2 text-neo-cream/60 hover:text-neo-orange mb-4 text-sm">
              <ArrowLeft className="w-4 h-4" />
              {t('silentReport.backToDashboard')}
            </Link>
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="neo-badge-orange mb-2 sm:mb-3 text-xs sm:text-sm">
                  <Radio className="w-3 h-3 sm:w-4 sm:h-4" />
                  {t('silentReport.title')}
                </div>
                <h1 className="text-2xl sm:text-3xl md:text-4xl font-heading font-bold text-neo-cream mb-1 sm:mb-2">
                  {t('silentReport.title')}
                </h1>
                <p className="text-sm sm:text-base text-neo-cream/60">
                  {t('silentReport.subtitle')}
                </p>
              </div>
              <button
                onClick={() => setShowInstructions(!showInstructions)}
                className={`p-2 sm:p-3 border-[2px] border-neo-cream/30 transition-colors flex-shrink-0 ${showInstructions ? 'bg-neo-orange text-neo-navy' : 'text-neo-cream hover:border-neo-orange'}`}
              >
                <HelpCircle className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="py-6 sm:py-10 bg-neo-cream">
        <div className="container mx-auto px-4">
          <div className="max-w-2xl mx-auto space-y-4 sm:space-y-6">
            
            {/* Instructions */}
            {showInstructions && (
              <NeoCard variant="navy" className="p-4 sm:p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 bg-neo-orange flex items-center justify-center flex-shrink-0">
                    <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-neo-navy" />
                  </div>
                  <h3 className="font-heading font-bold text-neo-cream text-sm sm:text-lg">{t('silentReport.howItWorks')}</h3>
                </div>
                
                <div className="grid grid-cols-2 gap-3 sm:gap-4 mb-4">
                  <div className="flex items-center gap-2 sm:gap-3 p-2 sm:p-3 bg-neo-cream/10 border-l-[3px] border-neo-orange">
                    <span className="font-mono bg-neo-cream text-neo-navy px-2 sm:px-3 py-1 border-[2px] border-neo-navy text-lg sm:text-xl font-bold">•</span>
                    <div>
                      <p className="text-neo-cream font-bold text-xs sm:text-sm">{t('silentReport.shortTap')}</p>
                      <p className="text-neo-cream/60 text-[10px] sm:text-xs">&lt; 0.5s</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 sm:gap-3 p-2 sm:p-3 bg-neo-cream/10 border-l-[3px] border-neo-teal">
                    <span className="font-mono bg-neo-cream text-neo-navy px-2 sm:px-3 py-1 border-[2px] border-neo-navy text-lg sm:text-xl font-bold">—</span>
                    <div>
                      <p className="text-neo-cream font-bold text-xs sm:text-sm">{t('silentReport.longTap')}</p>
                      <p className="text-neo-cream/60 text-[10px] sm:text-xs">&gt; 0.5s</p>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-neo-cream/20">
                  <p className="font-bold text-neo-cream mb-3 text-xs sm:text-sm uppercase">{t('silentReport.quickCodes')}</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 sm:gap-3">
                    {Object.entries(patterns).map(([key, val]) => (
                      <div key={key} className="flex items-center gap-2 p-2 bg-neo-cream/5 border border-neo-cream/20">
                        <span className="font-mono text-neo-orange font-bold text-xs sm:text-sm">{val.code}</span>
                        <span className="text-neo-cream/80 text-[10px] sm:text-xs">{val.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </NeoCard>
            )}

            {/* Tap Area */}
            <NeoCard className="p-4 sm:p-6 overflow-hidden">
              <p className="text-[10px] sm:text-xs text-neo-navy/60 uppercase font-bold mb-3 sm:mb-4 text-center">{t('silentReport.tapZone')}</p>

              {/* Main Tap Button */}
              <button
                onMouseDown={handleTapStart}
                onMouseUp={handleTapEnd}
                onMouseLeave={() => holding && handleTapEnd()}
                onTouchStart={handleTapStart}
                onTouchEnd={handleTapEnd}
                className={`
                  w-full h-40 sm:h-48 border-[3px] sm:border-[4px] border-neo-navy transition-all duration-100 select-none
                  flex items-center justify-center
                  ${holding
                    ? 'bg-neo-orange shadow-none translate-x-[3px] translate-y-[3px] sm:translate-x-[4px] sm:translate-y-[4px]'
                    : 'bg-neo-cream shadow-neo-lg hover:bg-neo-cream/80'
                  }
                `}
              >
                <div className="text-center">
                  <Fingerprint className={`w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-2 transition-colors ${holding ? 'text-neo-navy' : 'text-neo-navy/30'}`} />
                  <p className="font-heading font-bold text-sm sm:text-lg text-neo-navy">
                    {holding ? t('silentReport.holding') : t('silentReport.tapHere')}
                  </p>
                  <p className="text-[10px] sm:text-xs text-neo-navy/50 mt-1">
                    {holding ? 'Release to record' : 'Hold for long tap'}
                  </p>
                </div>
              </button>

              {/* Pattern Display */}
              <div className="mt-4 sm:mt-6">
                <p className="text-[10px] sm:text-xs text-neo-navy/60 uppercase font-bold mb-2 text-center">{t('silentReport.yourPattern')}</p>
                <div className="min-h-[50px] sm:min-h-[60px] bg-neo-navy border-[2px] sm:border-[3px] border-neo-navy p-3 sm:p-4 flex items-center justify-center gap-2 sm:gap-3">
                  {taps.length === 0 ? (
                    <span className="text-neo-cream/40 text-xs sm:text-sm">{t('silentReport.waitingForTaps')}</span>
                  ) : (
                    taps.map((tap, i) => (
                      <span
                        key={i}
                        className={`
                          inline-block transition-all
                          ${tap === 'short'
                            ? 'w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-neo-orange'
                            : 'w-8 h-3 sm:w-12 sm:h-4 rounded-full bg-neo-teal'
                          }
                        `}
                      />
                    ))
                  )}
                </div>
                <p className="text-[10px] sm:text-xs text-neo-navy/40 mt-2 font-mono text-center">
                  {taps.map(t => t === 'short' ? '•' : '—').join(' ') || '—'}
                </p>
              </div>
            </NeoCard>

            {/* Decoded Result */}
            <NeoCard className="overflow-hidden">
              <div className="p-3 sm:p-4 bg-neo-navy border-b-[3px] border-neo-navy">
                <h3 className="font-heading font-bold text-neo-cream text-sm sm:text-base flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-neo-orange" />
                  {t('silentReport.decodedResult')}
                </h3>
              </div>
              <div className="p-4 sm:p-6 grid grid-cols-2 gap-3 sm:gap-4">
                <div>
                  <p className="text-[10px] sm:text-xs text-neo-navy/60 uppercase mb-2 font-bold">{t('silentReport.category')}</p>
                  <div className={`inline-flex items-center gap-2 px-3 py-2 border-[2px] font-bold text-xs sm:text-sm ${decodedCategory ? 'bg-neo-orange border-neo-navy text-neo-navy' : 'bg-neo-cream border-neo-navy/30 text-neo-navy/50'}`}>
                    {decodedCategory ? patterns[decodedCategory]?.label : t('silentReport.notDetected')}
                  </div>
                </div>
                <div>
                  <p className="text-[10px] sm:text-xs text-neo-navy/60 uppercase mb-2 font-bold">{t('silentReport.severity')}</p>
                  <div className={`inline-flex items-center gap-2 px-3 py-2 border-[2px] font-bold text-xs sm:text-sm uppercase ${
                    decodedSeverity === 'high' ? 'bg-neo-maroon border-neo-navy text-neo-cream' :
                    decodedSeverity === 'medium' ? 'bg-neo-orange border-neo-navy text-neo-navy' :
                    decodedSeverity === 'low' ? 'bg-neo-teal border-neo-navy text-neo-cream' :
                    'bg-neo-cream border-neo-navy/30 text-neo-navy/50'
                  }`}>
                    {decodedSeverity || t('silentReport.notDetected')}
                  </div>
                </div>
              </div>
            </NeoCard>

            {/* Actions */}
            <div className="flex gap-3 sm:gap-4">
              <NeoButton onClick={resetTaps} variant="navy" className="flex-1 text-xs sm:text-sm">
                <RotateCcw className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                {t('common.reset')}
              </NeoButton>
              <NeoButton
                onClick={handleSubmit}
                variant="orange"
                className="flex-1 text-xs sm:text-sm"
                disabled={!decodedCategory}
              >
                <Send className="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" />
                {t('silentReport.submitSilentReport')}
              </NeoButton>
            </div>

            {/* Privacy Note */}
            <NeoCard variant="teal" className="p-3 sm:p-4">
              <div className="flex items-start gap-3">
                <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-neo-cream flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold text-neo-cream text-xs sm:text-sm mb-1">Zero-Knowledge Transmission</p>
                  <p className="text-neo-cream/70 text-[10px] sm:text-xs">
                    Your pattern is encoded locally and transmitted anonymously. No audio, text, or identifiable data is collected.
                  </p>
                </div>
              </div>
            </NeoCard>
          </div>
        </div>
      </section>
    </Layout>
  );
}
