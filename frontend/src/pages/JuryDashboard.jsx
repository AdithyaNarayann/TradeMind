import { useState, useEffect } from 'react';
import { Scale, ThumbsUp, ThumbsDown, Clock, Users, Award, AlertTriangle, Gavel, CheckCircle, Loader2 } from 'lucide-react';
import Layout from '../components/Layout';
import NeoCard from '../components/NeoCard';
import NeoButton from '../components/NeoButton';
import { useI18n } from '../context/I18nContext';
import { getJuryReports, submitJuryVote, getJuryStats, getUserJuryVotes, getReputationData } from '../lib/api';

export default function JuryDashboard() {
  const { t } = useI18n();
  const [selectedDispute, setSelectedDispute] = useState(null);
  const [hasVoted, setHasVoted] = useState({});
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [votingInProgress, setVotingInProgress] = useState({});
  
  // User stats
  const [userRep, setUserRep] = useState(50);
  const [voteWeight, setVoteWeight] = useState(5);
  const [casesJudged, setCasesJudged] = useState(0);
  const [successRate, setSuccessRate] = useState(0);
  
  // TODO: Get wallet from auth context - for now using a placeholder
  const walletAddress = localStorage.getItem('walletAddress') || '';

  useEffect(() => {
    fetchCases();
    if (walletAddress) {
      fetchUserStats();
      fetchUserVotes();
    }
  }, [walletAddress]);

  const fetchCases = async () => {
    try {
      setLoading(true);
      const reports = await getJuryReports();
      
      // Transform API reports to display format
      const transformedCases = reports.map((report, index) => ({
        id: `CASE-${String(index + 1).padStart(3, '0')}`,
        reportId: report.sessionId,
        category: report.aiAnalysis?.category || 'Pending Analysis',
        severity: report.aiAnalysis?.urgencyScore || 5,
        status: 'active',
        timeLeft: 'Active',
        votesValid: report.votes?.validPercent || 0,
        votesInvalid: report.votes?.invalidPercent || 0,
        totalVoters: report.votes?.totalVoters || 0,
        reporterRep: report.reporterReputation || 50,
        description: report.aiAnalysis?.reasoning || 'Report pending analysis by authorities.',
        authorityReason: 'Under review by community jury',
        reporterAppeal: 'Awaiting community verdict.',
        dbId: report._id,
        cid: report.cid,
        txHash: report.txHash,
        reporterWallet: report.reporterWallet,
        createdAt: report.createdAt
      }));
      
      setCases(transformedCases);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch jury cases:', err);
      setError('Failed to load cases');
    } finally {
      setLoading(false);
    }
  };

  const fetchUserStats = async () => {
    try {
      // Fetch both jury stats and full reputation data
      const [stats, repData] = await Promise.all([
        getJuryStats(walletAddress),
        getReputationData(walletAddress)
      ]);
      
      // Use jury reputation for jury-related stats
      setUserRep(repData.juryReputation || stats.reputation || 50);
      setVoteWeight(repData.voteWeight || stats.voteWeight || 5);
      setCasesJudged(repData.juryVotes || stats.casesJudged || 0);
      setSuccessRate(stats.successRate || 0);
    } catch (err) {
      console.error('Failed to fetch user stats:', err);
    }
  };

  const fetchUserVotes = async () => {
    try {
      const votes = await getUserJuryVotes(walletAddress);
      setHasVoted(votes);
    } catch (err) {
      console.error('Failed to fetch user votes:', err);
    }
  };

  const handleVote = async (dbId, vote) => {
    if (!walletAddress) {
      alert('Please connect your wallet to vote');
      return;
    }
    
    setVotingInProgress(prev => ({ ...prev, [dbId]: true }));
    
    try {
      const result = await submitJuryVote(dbId, vote, walletAddress);
      
      if (result.success) {
        setHasVoted(prev => ({ ...prev, [dbId]: vote }));
        // Refresh cases to get updated vote counts
        fetchCases();
        fetchUserStats();
      } else {
        alert(result.error || 'Failed to submit vote');
      }
    } catch (err) {
      console.error('Vote submission failed:', err);
      alert('Failed to submit vote');
    } finally {
      setVotingInProgress(prev => ({ ...prev, [dbId]: false }));
    }
  };

  return (
    <Layout>
      {/* Hero Header */}
      <section className="bg-neo-navy py-6 sm:py-12 border-b-[4px] border-neo-navy">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex flex-col gap-4">
              <div>
                <div className="neo-badge-orange mb-2 sm:mb-4 text-xs sm:text-sm">
                  <Scale className="w-3 h-3 sm:w-4 sm:h-4" />
                  {t('jury.badge')}
                </div>
                <h1 className="text-2xl sm:text-4xl md:text-5xl font-heading font-bold text-neo-cream mb-1 sm:mb-2">
                  {t('jury.title')}
                </h1>
                <p className="text-sm sm:text-base text-neo-cream/60">
                  {t('jury.subtitle')}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* User Stats Bar */}
      <section className="bg-neo-teal border-b-[4px] border-neo-navy">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4">
            <div className="py-3 sm:py-6 text-center border-r-[2px] border-b-[2px] md:border-b-0 border-neo-navy">
              <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-cream">{userRep}</p>
              <p className="text-xs sm:text-sm text-neo-cream/70">{t('jury.yourRep')}</p>
            </div>
            <div className="py-3 sm:py-6 text-center border-b-[2px] md:border-b-0 md:border-r-[2px] border-neo-navy">
              <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-orange">{voteWeight}x</p>
              <p className="text-xs sm:text-sm text-neo-cream/70">{t('jury.voteWeight')}</p>
            </div>
            <div className="py-3 sm:py-6 text-center border-r-[2px] border-neo-navy">
              <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-cream">{casesJudged}</p>
              <p className="text-xs sm:text-sm text-neo-cream/70">{t('jury.casesJudged')}</p>
            </div>
            <div className="py-3 sm:py-6 text-center">
              <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-orange">{successRate}%</p>
              <p className="text-xs sm:text-sm text-neo-cream/70">{t('jury.successRate')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <section className="py-12 bg-neo-cream">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            {/* Filter Tabs */}
            <div className="flex items-center gap-4 mb-8">
              <NeoButton variant="navy" size="sm">{t('jury.allDisputes')}</NeoButton>
              <NeoButton variant="default" size="sm">{t('jury.active')} ({cases.filter(d => d.status === 'active').length})</NeoButton>
              <NeoButton variant="default" size="sm">{t('jury.ended')}</NeoButton>
            </div>

            {/* Loading State */}
            {loading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-neo-navy" />
                <span className="ml-3 text-neo-navy font-semibold">Loading cases...</span>
              </div>
            )}

            {/* Error State */}
            {error && !loading && (
              <NeoCard variant="maroon" className="p-6 text-center">
                <p className="text-neo-cream font-semibold">{error}</p>
                <NeoButton variant="orange" size="sm" className="mt-4" onClick={fetchCases}>
                  Try Again
                </NeoButton>
              </NeoCard>
            )}

            {/* Empty State */}
            {!loading && !error && cases.length === 0 && (
              <NeoCard className="p-8 text-center">
                <Scale className="w-12 h-12 mx-auto text-neo-navy/40 mb-4" />
                <h3 className="font-heading font-bold text-xl text-neo-navy mb-2">No Cases Under Review</h3>
                <p className="text-neo-navy/60">There are currently no cases awaiting community jury review.</p>
              </NeoCard>
            )}

            {/* Disputes List */}
            {!loading && !error && cases.length > 0 && (
            <div className="space-y-6">
              {cases.map((dispute) => (
                <NeoCard
                  key={dispute.id}
                  className={`overflow-hidden ${dispute.status === 'ended' ? 'opacity-80' : ''}`}
                >
                  {/* Header */}
                  <div className="p-4 border-b-[3px] border-neo-navy bg-neo-navy flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-neo-orange flex items-center justify-center">
                        <Gavel className="w-5 h-5 text-neo-navy" />
                      </div>
                      <div>
                        <p className="font-heading font-bold text-neo-cream">{dispute.id}</p>
                        <p className="text-xs text-neo-cream/60">Report: {dispute.reportId}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`neo-badge ${dispute.status === 'active' ? 'bg-neo-orange text-neo-navy' : 'bg-neo-cream/20 text-neo-cream'} border-neo-cream`}>
                        {dispute.status === 'active' ? t('jury.active') : t('jury.ended')}
                      </span>
                      {dispute.status === 'active' && (
                        <div className="flex items-center gap-1 text-neo-cream">
                          <Clock className="w-4 h-4" />
                          <span className="font-mono font-bold">{dispute.timeLeft}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-4 grid md:grid-cols-2 gap-4">
                    {/* Left: Report Details */}
                    <div className="space-y-4">
                      <div>
                        <p className="text-xs uppercase font-bold text-neo-navy/60 mb-2">{t('jury.categorySeverity')}</p>
                        <div className="flex items-center gap-2">
                          <span className="neo-badge-orange">{dispute.category}</span>
                          <span className="neo-badge-navy">{dispute.severity}/10</span>
                        </div>
                      </div>

                      <div>
                        <p className="text-xs uppercase font-bold text-neo-navy/60 mb-1">{t('jury.reportSummary')}</p>
                        <p className="text-sm text-neo-navy/80">{dispute.description}</p>
                      </div>

                      <div className="flex items-center gap-2">
                        <p className="text-xs text-neo-navy/60">{t('jury.reporterRep')}</p>
                        <span className="font-bold text-neo-teal">{dispute.reporterRep}</span>
                      </div>
                    </div>

                    {/* Right: Dispute Details */}
                    <div className="space-y-4">
                      <NeoCard variant="maroon" className="p-3">
                        <p className="text-xs uppercase font-bold text-neo-cream/80 mb-1">{t('jury.authorityRejection')}</p>
                        <p className="text-sm text-neo-cream">{dispute.authorityReason}</p>
                      </NeoCard>

                      <NeoCard variant="teal" className="p-3">
                        <p className="text-xs uppercase font-bold text-neo-cream/80 mb-1">{t('jury.reporterAppeal')}</p>
                        <p className="text-sm text-neo-cream">{dispute.reporterAppeal}</p>
                      </NeoCard>
                    </div>
                  </div>

                  {/* Voting Section */}
                  <div className="p-4 border-t-[3px] border-neo-navy bg-neo-cream">
                    {/* Vote Progress */}
                    <div className="mb-4">
                      <div className="flex items-center justify-between text-sm mb-2">
                        <span className="flex items-center gap-1 text-neo-teal font-bold">
                          <ThumbsUp className="w-4 h-4" />
                          {t('jury.valid')} ({dispute.votesValid}%)
                        </span>
                        <span className="flex items-center gap-1 text-neo-navy/60">
                          <Users className="w-4 h-4" />
                          {dispute.totalVoters} {t('jury.voters')}
                        </span>
                        <span className="flex items-center gap-1 text-neo-maroon font-bold">
                          {t('jury.invalid')} ({dispute.votesInvalid}%)
                          <ThumbsDown className="w-4 h-4" />
                        </span>
                      </div>
                      <div className="h-5 bg-neo-cream border-[3px] border-neo-navy flex overflow-hidden">
                        <div
                          className="bg-neo-teal h-full transition-all"
                          style={{ width: `${dispute.votesValid}%` }}
                        />
                        <div
                          className="bg-neo-maroon h-full transition-all"
                          style={{ width: `${dispute.votesInvalid}%` }}
                        />
                      </div>
                    </div>

                    {/* Vote Buttons or Result */}
                    {dispute.status === 'ended' ? (
                      <NeoCard variant={dispute.verdict === 'valid' ? 'teal' : 'maroon'} className="p-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          {dispute.verdict === 'valid' ? (
                            <CheckCircle className="w-5 h-5 text-neo-cream" />
                          ) : (
                            <ThumbsDown className="w-5 h-5 text-neo-cream" />
                          )}
                          <p className="font-heading font-bold text-neo-cream">
                            {t('jury.verdict')} {dispute.verdict === 'valid' ? t('jury.reportValid') : t('jury.reportInvalid')}
                          </p>
                        </div>
                      </NeoCard>
                    ) : hasVoted[dispute.dbId] ? (
                      <NeoCard variant="teal" className="p-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Award className="w-5 h-5 text-neo-cream" />
                          <p className="font-heading font-bold text-neo-cream">
                            {t('jury.youVoted')} {hasVoted[dispute.dbId] === 'valid' ? t('jury.valid') : t('jury.invalid')}
                          </p>
                        </div>
                      </NeoCard>
                    ) : votingInProgress[dispute.dbId] ? (
                      <div className="flex items-center justify-center py-4">
                        <Loader2 className="w-6 h-6 animate-spin text-neo-navy" />
                        <span className="ml-2 font-semibold text-neo-navy">Submitting vote...</span>
                      </div>
                    ) : (
                      <div className="flex gap-4">
                        <NeoButton
                          variant="teal"
                          className="flex-1"
                          onClick={() => handleVote(dispute.dbId, 'valid')}
                        >
                          <ThumbsUp className="w-5 h-5 mr-2" />
                          {t('jury.voteValid')}
                        </NeoButton>
                        <NeoButton
                          variant="maroon"
                          className="flex-1"
                          onClick={() => handleVote(dispute.dbId, 'invalid')}
                        >
                          <ThumbsDown className="w-5 h-5 mr-2" />
                          {t('jury.voteInvalid')}
                        </NeoButton>
                      </div>
                    )}
                  </div>
                </NeoCard>
              ))}
            </div>
            )}

            {/* Info Banner */}
            <NeoCard variant="navy" className="p-6 mt-8">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-neo-orange flex items-center justify-center flex-shrink-0">
                  <AlertTriangle className="w-6 h-6 text-neo-navy" />
                </div>
                <div>
                  <h4 className="font-heading font-bold text-neo-cream mb-2">{t('jury.reputationWeightedVoting')}</h4>
                  <p className="text-neo-cream/70 text-sm">
                    {t('jury.votingExplanation')}
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
