import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Shield, Award, TrendingUp, TrendingDown, CheckCircle, XCircle, Info, Loader2, ArrowLeft, Star } from 'lucide-react';
import Layout from '../components/Layout';
import NeoCard from '../components/NeoCard';
import NeoButton from '../components/NeoButton';
import { useI18n } from '../context/I18nContext';
import { useSession } from '../context/SessionContext';
import { getReputationData } from '../lib/api';

export default function ReputationPage() {
  const { t } = useI18n();
  const { walletAddress, loading: sessionLoading } = useSession();
  const navigate = useNavigate();
  const [showExplainer, setShowExplainer] = useState(false);

  const reputationTiers = [
    { name: t('reputation.tiers.newcomer'), min: 0, max: 25, color: 'bg-neo-cream' },
    { name: t('reputation.tiers.regular'), min: 26, max: 50, color: 'bg-neo-teal/50' },
    { name: t('reputation.tiers.trusted'), min: 51, max: 75, color: 'bg-neo-teal' },
    { name: t('reputation.tiers.expert'), min: 76, max: 90, color: 'bg-neo-orange' },
    { name: t('reputation.tiers.guardian'), min: 91, max: 100, color: 'bg-neo-maroon' },
  ];

  const [loading, setLoading] = useState(true);
  const [reputation, setReputation] = useState({
    ensAlias: 'sayless-xxxx.eth',
    score: 0,
    tier: 'Newcomer',
    totalReports: 0,
    acceptedReports: 0,
    rejectedReports: 0,
    juryVotes: 0,
    correctVotes: 0,
    rewardsEarned: '0 ETH',
    penaltiesReceived: '0 ETH',
    recentActivity: []
  });

  useEffect(() => {
    if (sessionLoading) return;
    
    const wallet = walletAddress || localStorage.getItem('walletAddress');
    if (!wallet) {
      navigate('/reporter');
      return;
    }

    async function loadData() {
      try {
        const data = await getReputationData(wallet);
        if (!data.error) {
          setReputation(data);
        }
      } catch (error) {
        console.error('Failed to load reputation data:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [sessionLoading, walletAddress, navigate]);

  const currentTier = reputationTiers.find(
    t => reputation.score >= t.min && reputation.score <= t.max
  ) || reputationTiers[0];

  const acceptRate = reputation.totalReports > 0 
    ? Math.round((reputation.acceptedReports / reputation.totalReports) * 100) 
    : 0;
  const voteAccuracy = reputation.juryVotes > 0 
    ? Math.round((reputation.correctVotes / reputation.juryVotes) * 100) 
    : 0;

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="w-10 h-10 animate-spin text-neo-teal" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Hero Header */}
      <section className="bg-neo-navy py-6 sm:py-10 border-b-[4px] border-neo-navy">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <Link to="/reporter" className="inline-flex items-center gap-2 text-neo-cream/60 hover:text-neo-orange mb-4 text-sm">
              <ArrowLeft className="w-4 h-4" />
              Back to Dashboard
            </Link>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <div className="neo-badge-teal mb-2 sm:mb-3 text-xs sm:text-sm">
                  <Shield className="w-3 h-3 sm:w-4 sm:h-4" />
                  Reputation System
                </div>
                <h1 className="text-2xl sm:text-3xl md:text-4xl font-heading font-bold text-neo-cream">
                  {t('reputation.title')}
                </h1>
              </div>
              <button
                onClick={() => setShowExplainer(!showExplainer)}
                className={`self-start sm:self-auto p-2 sm:p-3 border-[2px] border-neo-cream/30 transition-colors ${showExplainer ? 'bg-neo-orange text-neo-navy' : 'text-neo-cream hover:border-neo-orange'}`}
              >
                <Info className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="py-6 sm:py-10 bg-neo-cream">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto space-y-4 sm:space-y-6">
            
            {/* Identity Badge */}
            <NeoCard variant="navy" className="p-4 sm:p-6">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 sm:gap-6">
                <div className="flex items-center gap-3 sm:gap-4">
                  <div className="w-12 h-12 sm:w-16 sm:h-16 bg-neo-teal border-[2px] sm:border-[3px] border-neo-cream flex items-center justify-center flex-shrink-0">
                    <Shield className="w-6 h-6 sm:w-8 sm:h-8 text-neo-cream" />
                  </div>
                  <div>
                    <p className="text-[10px] sm:text-xs text-neo-cream/60 uppercase">{t('reputation.anonymousIdentity')}</p>
                    <p className="font-mono font-bold text-lg sm:text-2xl text-neo-orange">{reputation.ensAlias}</p>
                  </div>
                </div>
                <div className="text-center sm:text-right">
                  <p className="text-4xl sm:text-6xl font-heading font-bold text-neo-cream">{reputation.score}</p>
                  <span className={`inline-block px-3 py-1 text-xs sm:text-sm font-bold border-[2px] border-neo-navy ${currentTier.color} text-neo-navy`}>
                    {currentTier.name}
                  </span>
                </div>
              </div>
            </NeoCard>

            {/* Score Meter */}
            <NeoCard className="p-4 sm:p-6">
              <div className="flex items-center justify-between mb-3 sm:mb-4">
                <h3 className="font-heading font-bold text-sm sm:text-lg text-neo-navy">{t('reputation.reputationScore')}</h3>
              </div>

              {/* Score Bar */}
              <div className="relative mb-6 sm:mb-8 mt-6 sm:mt-8">
                <div className="h-6 sm:h-8 bg-neo-cream border-[2px] sm:border-[3px] border-neo-navy flex overflow-hidden">
                  {reputationTiers.map((tier, i) => (
                    <div
                      key={tier.name}
                      className={`${tier.color} flex-1 ${i < reputationTiers.length - 1 ? 'border-r-[1px] sm:border-r-[2px] border-neo-navy' : ''}`}
                    />
                  ))}
                </div>
                {/* Indicator */}
                <div
                  className="absolute top-0 w-1 h-6 sm:h-8 bg-neo-navy"
                  style={{ left: `${reputation.score}%`, transform: 'translateX(-50%)' }}
                >
                  <div className="absolute -top-6 sm:-top-7 left-1/2 -translate-x-1/2 bg-neo-orange text-neo-navy px-2 py-0.5 text-[10px] sm:text-xs font-bold border-[2px] border-neo-navy">
                    {reputation.score}
                  </div>
                </div>
              </div>

              {/* Tier Labels */}
              <div className="flex justify-between text-[8px] sm:text-xs text-neo-navy/60">
                {reputationTiers.map(tier => (
                  <span key={tier.name} className="text-center">{tier.name}</span>
                ))}
              </div>

              {/* Explainer */}
              {showExplainer && (
                <NeoCard variant="teal" className="mt-4 p-3 sm:p-4">
                  <h4 className="font-bold mb-2 text-neo-cream text-sm sm:text-base">{t('reputation.howItWorks')}</h4>
                  <ul className="text-xs sm:text-sm space-y-1 text-neo-cream/80">
                    <li className="flex items-center gap-2">
                      <span className="text-neo-orange">+5</span>
                      <span>{t('reputation.verifiedReports')}</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-neo-maroon">-3</span>
                      <span>{t('reputation.rejectedReports')}</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-neo-orange">+2</span>
                      <span>{t('reputation.correctJuryVotes')}</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="text-neo-maroon">-1</span>
                      <span>{t('reputation.wrongJuryVotes')}</span>
                    </li>
                  </ul>
                </NeoCard>
              )}
            </NeoCard>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
              {/* Report Stats */}
              <NeoCard className="overflow-hidden">
                <div className="p-3 sm:p-4 bg-neo-navy border-b-[3px] border-neo-navy">
                  <h3 className="font-heading font-bold text-sm sm:text-base text-neo-cream">{t('reputation.reportStatistics')}</h3>
                </div>
                <div className="p-4 sm:p-6 space-y-3 sm:space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-neo-navy/70 text-xs sm:text-sm">{t('reputation.totalReports')}</span>
                    <span className="font-bold text-lg sm:text-xl text-neo-navy">{reputation.totalReports}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-neo-teal text-xs sm:text-sm">
                      <CheckCircle className="w-3 h-3 sm:w-4 sm:h-4" />
                      {t('reputation.accepted')}
                    </span>
                    <span className="font-bold text-lg sm:text-xl text-neo-teal">{reputation.acceptedReports}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-neo-maroon text-xs sm:text-sm">
                      <XCircle className="w-3 h-3 sm:w-4 sm:h-4" />
                      {t('reputation.rejected')}
                    </span>
                    <span className="font-bold text-lg sm:text-xl text-neo-maroon">{reputation.rejectedReports}</span>
                  </div>

                  {/* Accept Rate Bar */}
                  <div className="pt-2 border-t border-neo-navy/20">
                    <div className="flex items-center justify-between text-[10px] sm:text-xs mb-1">
                      <span className="text-neo-navy/70">{t('reputation.acceptanceRate')}</span>
                      <span className="font-bold text-neo-navy">{acceptRate}%</span>
                    </div>
                    <div className="h-3 sm:h-4 bg-neo-cream border-[2px] border-neo-navy overflow-hidden">
                      <div
                        className="h-full bg-neo-teal transition-all"
                        style={{ width: `${acceptRate}%` }}
                      />
                    </div>
                  </div>
                </div>
              </NeoCard>

              {/* Jury Stats */}
              <NeoCard className="overflow-hidden">
                <div className="p-3 sm:p-4 bg-neo-teal border-b-[3px] border-neo-navy">
                  <h3 className="font-heading font-bold text-sm sm:text-base text-neo-cream">{t('reputation.juryParticipation')}</h3>
                </div>
                <div className="p-4 sm:p-6 space-y-3 sm:space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-neo-navy/70 text-xs sm:text-sm">{t('reputation.totalVotes')}</span>
                    <span className="font-bold text-lg sm:text-xl text-neo-navy">{reputation.juryVotes}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-neo-teal text-xs sm:text-sm">
                      <TrendingUp className="w-3 h-3 sm:w-4 sm:h-4" />
                      {t('reputation.correct')}
                    </span>
                    <span className="font-bold text-lg sm:text-xl text-neo-teal">{reputation.correctVotes}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-neo-maroon text-xs sm:text-sm">
                      <TrendingDown className="w-3 h-3 sm:w-4 sm:h-4" />
                      {t('reputation.incorrect')}
                    </span>
                    <span className="font-bold text-lg sm:text-xl text-neo-maroon">{reputation.juryVotes - reputation.correctVotes}</span>
                  </div>

                  {/* Accuracy Bar */}
                  <div className="pt-2 border-t border-neo-navy/20">
                    <div className="flex items-center justify-between text-[10px] sm:text-xs mb-1">
                      <span className="text-neo-navy/70">{t('reputation.voteAccuracy')}</span>
                      <span className="font-bold text-neo-navy">{voteAccuracy}%</span>
                    </div>
                    <div className="h-3 sm:h-4 bg-neo-cream border-[2px] border-neo-navy overflow-hidden">
                      <div
                        className="h-full bg-neo-orange transition-all"
                        style={{ width: `${voteAccuracy}%` }}
                      />
                    </div>
                  </div>
                </div>
              </NeoCard>
            </div>

            {/* Earnings */}
            <div className="grid grid-cols-2 gap-3 sm:gap-4">
              <NeoCard variant="teal" className="p-3 sm:p-6">
                <div className="flex items-center gap-2 sm:gap-3 mb-1 sm:mb-2">
                  <Award className="w-4 h-4 sm:w-6 sm:h-6 text-neo-cream" />
                  <span className="font-heading font-bold text-neo-cream text-xs sm:text-sm">{t('reputation.rewardsEarned')}</span>
                </div>
                <p className="text-xl sm:text-3xl font-heading font-bold text-neo-orange">{reputation.rewardsEarned}</p>
              </NeoCard>

              <NeoCard variant="maroon" className="p-3 sm:p-6">
                <div className="flex items-center gap-2 sm:gap-3 mb-1 sm:mb-2">
                  <TrendingDown className="w-4 h-4 sm:w-6 sm:h-6 text-neo-cream" />
                  <span className="font-heading font-bold text-neo-cream text-xs sm:text-sm">{t('reputation.penalties')}</span>
                </div>
                <p className="text-xl sm:text-3xl font-heading font-bold text-neo-cream">{reputation.penaltiesReceived}</p>
              </NeoCard>
            </div>

            {/* Recent Activity */}
            <NeoCard className="overflow-hidden">
              <div className="p-3 sm:p-4 border-b-[3px] border-neo-navy bg-neo-navy">
                <h3 className="font-heading font-bold text-sm sm:text-base text-neo-cream">{t('reputation.recentActivity')}</h3>
              </div>
              <div className="divide-y-[2px] divide-neo-navy/20">
                {(reputation.recentActivity || []).length === 0 ? (
                  <div className="p-6 sm:p-8 text-center text-neo-navy/50">
                    <Star className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-xs sm:text-sm">No recent activity yet</p>
                  </div>
                ) : (
                  (reputation.recentActivity || []).map((activity, i) => (
                    <div key={i} className="p-3 sm:p-4 flex items-center justify-between">
                      <div className="flex items-center gap-2 sm:gap-3">
                        <div className={`
                          w-6 h-6 sm:w-8 sm:h-8 border-[2px] border-neo-navy flex items-center justify-center flex-shrink-0
                          ${activity.change.startsWith('+') ? 'bg-neo-teal' : 'bg-neo-maroon'}
                        `}>
                          {activity.change.startsWith('+') ? (
                            <TrendingUp className="w-3 h-3 sm:w-4 sm:h-4 text-neo-cream" />
                          ) : (
                            <TrendingDown className="w-3 h-3 sm:w-4 sm:h-4 text-neo-cream" />
                          )}
                        </div>
                        <div>
                          <p className="font-bold text-xs sm:text-sm text-neo-navy">{activity.description}</p>
                          <p className="text-[10px] sm:text-xs text-neo-navy/50">{activity.date}</p>
                        </div>
                      </div>
                      <span className={`font-mono font-bold text-sm sm:text-base ${activity.change.startsWith('+') ? 'text-neo-teal' : 'text-neo-maroon'}`}>
                        {activity.change}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </NeoCard>
          </div>
        </div>
      </section>
    </Layout>
  );
}
