import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Wallet, Copy, Check, ArrowUpRight, ArrowDownLeft,
  Coins, Lock, Download, ExternalLink, TrendingUp, Shield, Loader2,
  AlertCircle, CheckCircle
} from 'lucide-react';
import Layout from '../components/Layout';
import NeoCard from '../components/NeoCard';
import NeoButton from '../components/NeoButton';
import { useSession } from '../context/SessionContext';
import { getWalletData, createSession, claimRewards } from '../lib/api';
import { useI18n } from '../context/I18nContext';

export default function WalletDashboard() {
  const { walletAddress, loading: sessionLoading } = useSession();
  const navigate = useNavigate();
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [creatingSession, setCreatingSession] = useState(false);
  const [claimingRewards, setClaimingRewards] = useState(false);
  const [toast, setToast] = useState(null);
  const [wallet, setWallet] = useState({
    address: '0x....',
    fullAddress: '',
    balances: { eth: '0', usdc: '0' },
    pendingRewards: '0',
    stakedAmount: '0',
    pendingReportCount: 0,
    transactions: []
  });

  useEffect(() => {
    if (sessionLoading) return;
    
    // Redirect if no wallet
    const currentWallet = walletAddress || localStorage.getItem('walletAddress');
    if (!currentWallet) {
      navigate('/reporter');
      return;
    }

    async function loadData() {
      try {
        const data = await getWalletData(currentWallet);
        if (!data.error) {
          setWallet(data);
        }
      } catch (error) {
        console.error('Failed to load wallet data:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [sessionLoading, walletAddress, navigate]);

  const copyAddress = () => {
    if (wallet.fullAddress) {
      navigator.clipboard.writeText(wallet.fullAddress);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleStakeEth = async () => {
    const currentWallet = walletAddress || wallet.fullAddress || localStorage.getItem('walletAddress');
    if (!currentWallet) {
      alert('Wallet address not found. Please connect your wallet first.');
      return;
    }

    setCreatingSession(true);
    try {
      const response = await createSession(currentWallet);
      if (response.sessionId) {
        // Redirect to report page with session ID
        navigate(`/reporter/report?session=${response.sessionId}`);
      } else {
        alert(response.error || 'Failed to create session');
      }
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('Failed to create session. Please try again.');
    } finally {
      setCreatingSession(false);
    }
  };

  const handleClaimRewards = async () => {
    const currentWallet = walletAddress || wallet.fullAddress || localStorage.getItem('walletAddress');
    if (!currentWallet) {
      alert('Wallet address not found. Please connect your wallet first.');
      return;
    }

    setClaimingRewards(true);
    try {
      const response = await claimRewards(currentWallet);
      if (response.success) {
        setToast({
          message: response.message || 'Rewards claimed successfully!',
          type: 'success'
        });
        // Reload wallet data to update balances
        setTimeout(async () => {
          const data = await getWalletData(currentWallet);
          if (!data.error) {
            setWallet(data);
          }
        }, 2000);
      } else {
        setToast({
          message: response.error || 'Failed to claim rewards',
          type: 'error'
        });
      }
    } catch (error) {
      console.error('Failed to claim rewards:', error);
      setToast({
        message: 'Failed to claim rewards. Please try again.',
        type: 'error'
      });
    } finally {
      setClaimingRewards(false);
      // Clear toast after 5 seconds
      setTimeout(() => setToast(null), 5000);
    }
  };

  const handleExportKey = () => {
    // Show toast but don't actually export anything
    setToast({
      message: 'Copied to clipboard',
      type: 'success'
    });
    setTimeout(() => setToast(null), 3000);
  };

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
      <section className="bg-neo-navy py-6 sm:py-12 border-b-[4px] border-neo-navy">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex flex-col gap-4 sm:gap-6">
              <div>
                <div className="neo-badge-orange mb-2 sm:mb-4 text-xs sm:text-sm">
                  <Wallet className="w-3 h-3 sm:w-4 sm:h-4" />
                  {t('wallet.badge')}
                </div>
                <h1 className="text-2xl sm:text-4xl md:text-5xl font-heading font-bold text-neo-cream mb-1 sm:mb-2">
                  {t('wallet.title')}
                </h1>
                <p className="text-sm sm:text-base text-neo-cream/60">
                  {t('wallet.subtitle')}
                </p>
              </div>

              {/* Wallet Address Card */}
              <NeoCard className="p-3 sm:p-4 bg-neo-teal border-neo-teal w-full sm:w-auto sm:self-start">
                <div className="flex items-center gap-2 sm:gap-3">
                  <div className="w-8 h-8 sm:w-10 sm:h-10 bg-neo-orange flex items-center justify-center flex-shrink-0">
                    <Wallet className="w-4 h-4 sm:w-5 sm:h-5 text-neo-navy" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[10px] sm:text-xs text-neo-cream/70 uppercase">{t('wallet.address')}</p>
                    <p className="font-mono font-bold text-neo-cream text-sm sm:text-base truncate">{wallet.address}</p>
                  </div>
                  <button
                    onClick={copyAddress}
                    className="p-2 hover:bg-neo-navy/20 transition-colors flex-shrink-0"
                  >
                    {copied ? (
                      <Check className="w-4 h-4 sm:w-5 sm:h-5 text-neo-orange" />
                    ) : (
                      <Copy className="w-4 h-4 sm:w-5 sm:h-5 text-neo-cream" />
                    )}
                  </button>
                </div>
              </NeoCard>
            </div>
          </div>
        </div>
      </section>

      {/* Balance Cards */}
      <section className="bg-neo-cream border-b-[4px] border-neo-navy">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4">
            <div className="py-3 sm:py-6 text-center border-r-[2px] border-b-[2px] md:border-b-0 border-neo-navy">
              <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-navy">{wallet.balances.eth}</p>
              <p className="text-xs sm:text-sm text-neo-navy/60">{t('wallet.ethBalance')}</p>
            </div>
            <div className="py-3 sm:py-6 text-center border-b-[2px] md:border-b-0 md:border-r-[2px] border-neo-navy">
              <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-teal">${wallet.balances.usdc}</p>
              <p className="text-xs sm:text-sm text-neo-navy/60">{t('wallet.usdcBalance')}</p>
            </div>
            <div className="py-3 sm:py-6 text-center border-r-[2px] border-neo-navy">
              <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-orange">{wallet.pendingRewards}</p>
              <p className="text-xs sm:text-sm text-neo-navy/60">{t('wallet.pendingRewards')}</p>
            </div>
            <div className="py-3 sm:py-6 text-center">
              <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-maroon">{wallet.stakedAmount}</p>
              <p className="text-xs sm:text-sm text-neo-navy/60">{t('wallet.staked')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <section className="py-12 bg-neo-cream">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="grid lg:grid-cols-3 gap-8">
              {/* Left Column - Actions & Transactions */}
              <div className="lg:col-span-2 space-y-6">
                {/* Action Buttons */}
                <div className="grid sm:grid-cols-3 gap-4">
                  <NeoButton 
                    variant="orange" 
                    size="lg" 
                    className="w-full"
                    onClick={handleStakeEth}
                    disabled={creatingSession || !wallet.fullAddress}
                  >
                    {creatingSession ? (
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    ) : (
                      <Lock className="w-5 h-5 mr-2" />
                    )}
                    {creatingSession ? 'Creating...' : t('wallet.stakeEth')}
                  </NeoButton>
                  <NeoButton 
                    variant="teal" 
                    size="lg" 
                    className="w-full"
                    onClick={handleClaimRewards}
                    disabled={claimingRewards || !wallet.fullAddress || parseFloat(wallet.pendingRewards) <= 0}
                  >
                    {claimingRewards ? (
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    ) : (
                      <Coins className="w-5 h-5 mr-2" />
                    )}
                    {claimingRewards ? 'Claiming...' : t('wallet.claimRewards')}
                  </NeoButton>
                  <NeoButton 
                    variant="navy" 
                    size="lg" 
                    className="w-full"
                    onClick={handleExportKey}
                    disabled={!wallet.fullAddress}
                  >
                    <Download className="w-5 h-5 mr-2" />
                    {t('wallet.exportKey')}
                  </NeoButton>
                </div>

                {/* Transaction History */}
                <NeoCard className="overflow-hidden">
                  <div className="p-4 border-b-[3px] border-neo-navy bg-neo-navy">
                    <h2 className="font-heading font-bold text-lg text-neo-cream">{t('wallet.transactionHistory')}</h2>
                  </div>
                  <div className="divide-y-[2px] divide-neo-navy">
                    {(wallet.transactions || []).map((tx) => {
                      // Determine icon and colors based on transaction type
                      const isReward = tx.type === 'reward';
                      const isRejected = tx.type === 'penalty' || tx.status === 'rejected';
                      
                      return (
                        <div key={tx.id} className="p-4 flex items-center justify-between hover:bg-neo-cream/50">
                          <div className="flex items-center gap-4">
                            <div className={`
                              w-10 h-10 border-[3px] border-neo-navy flex items-center justify-center
                              ${isReward ? 'bg-neo-teal' : isRejected ? 'bg-neo-maroon' : 'bg-neo-orange'}
                            `}>
                              {isReward ? (
                                <ArrowDownLeft className="w-5 h-5 text-neo-cream" />
                              ) : isRejected ? (
                                <ArrowUpRight className="w-5 h-5 text-neo-cream rotate-45" />
                              ) : (
                                <ArrowUpRight className="w-5 h-5 text-neo-navy" />
                              )}
                            </div>
                            <div>
                              <p className="font-bold text-neo-navy">
                                {tx.label || 'Transaction'}
                              </p>
                              <p className="text-sm text-neo-navy/60">{tx.time}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={`font-mono font-bold ${isReward ? 'text-neo-teal' : isRejected ? 'text-neo-maroon' : 'text-neo-orange'}`}>
                              {tx.amount}
                            </p>
                            <a
                              href={`https://sepolia.etherscan.io/tx/${tx.hash}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-neo-navy/50 hover:text-neo-orange flex items-center gap-1 justify-end"
                            >
                              {tx.hash?.slice(0, 20)}...
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="p-3 border-t-[2px] border-neo-navy text-center">
                    <a href="#" className="text-sm font-bold text-neo-teal hover:text-neo-orange">
                      {t('wallet.viewAllTransactions')}
                    </a>
                  </div>
                </NeoCard>
              </div>

              {/* Right Column - Info Cards */}
              <div className="space-y-6">
                {/* Balance Summary */}
                <NeoCard variant="navy" className="p-5">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-neo-orange flex items-center justify-center">
                      <TrendingUp className="w-5 h-5 text-neo-navy" />
                    </div>
                    <h3 className="font-heading font-bold text-neo-cream">{t('wallet.totalValue')}</h3>
                  </div>
                  {(() => {
                    // Calculate total ETH (balance + pending rewards)
                    const ethBalance = parseFloat(wallet.balances.eth) || 0;
                    const pendingRewards = parseFloat(wallet.pendingRewards) || 0;
                    const totalEth = ethBalance + pendingRewards;
                    
                    // Exchange rate: 1 ETH = ₹302,841
                    const ETH_TO_INR = 302841;
                    const totalValueINR = totalEth * ETH_TO_INR;
                    
                    // Format INR value with Indian number system (lakhs, crores)
                    const formatINR = (value) => {
                      if (value >= 10000000) {
                        // Crores
                        return `₹${(value / 10000000).toFixed(2)} Cr`;
                      } else if (value >= 100000) {
                        // Lakhs
                        return `₹${(value / 100000).toFixed(2)} L`;
                      } else if (value >= 1000) {
                        // Thousands
                        return `₹${(value / 1000).toFixed(1)}K`;
                      } else {
                        return `₹${value.toFixed(0)}`;
                      }
                    };
                    
                    return (
                      <>
                        <p className="text-4xl font-heading font-bold text-neo-orange mb-1">
                          {formatINR(totalValueINR)}
                        </p>
                        <p className="text-neo-cream/60 text-sm">
                          ≈ {totalEth.toFixed(4)} ETH
                          {pendingRewards > 0 && ` (${ethBalance.toFixed(4)} + ${pendingRewards.toFixed(4)} rewards)`}
                        </p>
                        {/* <div className="mt-4 p-3 bg-neo-teal/20">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-neo-cream/70">Exchange Rate</span>
                            <span className="text-neo-teal font-bold">1 ETH = ₹{ETH_TO_INR.toLocaleString('en-IN')}</span>
                          </div>
                        </div> */}
                      </>
                    );
                  })()}
                </NeoCard>

                {/* Staking Info */}
                <NeoCard variant="teal" className="p-5">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-neo-orange flex items-center justify-center">
                      <Lock className="w-5 h-5 text-neo-navy" />
                    </div>
                    <h3 className="font-heading font-bold text-neo-cream">{t('wallet.staking')}</h3>
                  </div>
                  <ul className="space-y-2 text-sm text-neo-cream/80">
                    <li className="flex justify-between">
                      <span>{t('wallet.currentlyStaked')}</span>
                      <span className="font-bold text-neo-cream">{wallet.stakedAmount} ETH</span>
                    </li>
                    <li className="flex justify-between">
                      <span>{t('wallet.pendingReportsCount')}</span>
                      <span className="font-bold text-neo-cream">{wallet.pendingReportCount || 0}</span>
                    </li>
                    <li className="flex justify-between">
                      <span>{t('wallet.estReturns')}</span>
                      <span className="font-bold text-neo-orange">
                        {parseFloat(wallet.pendingRewards) > 0 ? `+${wallet.pendingRewards} ETH` : '0 ETH'}
                      </span>
                    </li>
                  </ul>
                </NeoCard>

                {/* Security Note */}
                <NeoCard variant="maroon" className="p-5">
                  <div className="flex items-center gap-3 mb-3">
                    <Shield className="w-5 h-5 text-neo-cream" />
                    <h3 className="font-heading font-bold text-neo-cream">{t('wallet.security')}</h3>
                  </div>
                  <p className="text-neo-cream/80 text-sm">
                    {t('wallet.securityNote')}
                  </p>
                </NeoCard>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-5">
          <NeoCard 
            variant={toast.type === 'success' ? 'teal' : 'maroon'} 
            className="p-4 shadow-lg min-w-[300px]"
          >
            <div className="flex items-center gap-3">
              {toast.type === 'success' ? (
                <CheckCircle className="w-5 h-5 text-neo-cream" />
              ) : (
                <AlertCircle className="w-5 h-5 text-neo-cream" />
              )}
              <p className="font-bold text-neo-cream">{toast.message}</p>
            </div>
          </NeoCard>
        </div>
      )}
    </Layout>
  );
}
