import { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import {
  Shield, Lock, Upload, CheckCircle, AlertCircle,
  ExternalLink, ArrowLeft, FileText, AlertTriangle, Zap, X
} from 'lucide-react';
import Layout from '../components/Layout';
import NeoCard from '../components/NeoCard';
import NeoButton from '../components/NeoButton';
import { useSession } from '../context/SessionContext';
import { encryptWithNaCl, encryptFile } from '../lib/encryption';
import { checkSession, submitReport } from '../lib/api';
import { useI18n } from '../context/I18nContext';

export default function Report() {
  const { t } = useI18n();
  const { sessionId: storedSessionId, walletAddress: storedWallet, saveSession } = useSession();
  const { sessionId: paramSessionId } = useParams();
  const [searchParams] = useSearchParams();
  
  // Priority: URL param > query param > stored session
  const sessionId = paramSessionId || searchParams.get('session') || storedSessionId;

  const [category, setCategory] = useState('');
  const [severity, setSeverity] = useState(5);
  const [text, setText] = useState('');
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState('loading'); // loading, valid, encrypting, submitting, done, error
  const [walletAddress, setWalletAddress] = useState(storedWallet);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showWarning, setShowWarning] = useState(false);
  const fileInputRef = useRef(null);

  // Check session validity on mount
  useEffect(() => {
    async function validateSession() {
      // Guard: Don't re-check if already validated
      if (status === 'valid' || status === 'invalid') {
        return;
      }

      if (!sessionId || sessionId === 'DEMO-SESSION') {
        // Allow demo/dev mode if needed, or enforce strictness
        setStatus('valid');
        return;
      }

      try {
        const data = await checkSession(sessionId);
        if (data.valid) {
          setStatus('valid');
          if (data.wallet) {
            setWalletAddress(data.wallet);
            // Save session to context so wallet is available across all pages
            saveSession(sessionId, data.wallet, data.expiresAt);
          }
        } else {
          setStatus('invalid');
          setError(data.error || 'Invalid session');
        }
      } catch (err) {
        console.error('Session check failed', err);
        setStatus('invalid');
        setError('Could not verify session');
      }
    }

    validateSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]); // Removed saveSession from deps - it's now memoized and stable

  const crimeCategories = [
    { id: 'theft', label: t('report.categories.theft'), icon: '🔓' },
    { id: 'assault', label: t('report.categories.assault'), icon: '⚠️' },
    { id: 'fraud', label: t('report.categories.fraud'), icon: '💳' },
    { id: 'corruption', label: t('report.categories.corruption'), icon: '🏛️' },
    { id: 'harassment', label: t('report.categories.harassment'), icon: '🚨' },
    { id: 'drugs', label: t('report.categories.drugs'), icon: '💊' },
    { id: 'cybercrime', label: t('report.categories.cybercrime'), icon: '💻' },
    { id: 'other', label: t('report.categories.other'), icon: '📋' },
  ];

  // Handle file selection with validation
  const handleFileSelection = (newFiles) => {
    const MAX_SIZE = 10 * 1024 * 1024; // 10MB
    const validFiles = [];
    const errors = [];

    newFiles.forEach((file) => {
      if (file.size > MAX_SIZE) {
        errors.push(`${file.name} exceeds 10MB limit`);
      } else {
        validFiles.push(file);
      }
    });

    if (errors.length > 0) {
      setError(errors.join(', '));
    }

    if (validFiles.length > 0) {
      setFiles((prev) => [...prev, ...validFiles]);
      if (errors.length === 0) {
        setError(null);
      }
    }
  };

  const handleSubmit = async () => {
    if (!text.trim() || !category) {
      setError(t('report.selectCategoryAndEnter'));
      return;
    }
    setShowWarning(true);
  };

  const confirmSubmit = async () => {
    setShowWarning(false);

    try {
      setStatus('encrypting');
      setError(null);
      
      // Encrypt report and files (this is fast, no artificial delay needed)
      const encryptedReport = encryptWithNaCl(text);
      const encryptedFiles = await Promise.all(files.map(f => encryptFile(f)));
      const payload = {
        report: encryptedReport,
        category,
        severity,
        files: encryptedFiles,
        timestamp: Date.now()
      };
      
      // Submit to backend (this will show loading state naturally)
      setStatus('submitting');
      const data = await submitReport(sessionId, payload);
      
      if (data.success) {
        setResult(data);
        setStatus('done');
      } else {
        setError(data.error || 'Submission failed');
        setStatus('valid'); // Return to valid state to retry
      }
    } catch (err) {
      console.error(err);
      setError(err.message || 'An error occurred');
      setStatus('valid'); // Return to valid state to retry
    }
  };

  // Loading state
  if (status === 'loading') {
    return (
      <Layout>
        <div className="min-h-[80vh] flex items-center justify-center p-4 bg-neo-cream">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-neo-orange border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="font-heading font-bold text-neo-navy">Verifying Session...</p>
          </div>
        </div>
      </Layout>
    );
  }

  // Invalid state
  if (status === 'invalid') {
    return (
      <Layout>
        <div className="min-h-[80vh] flex items-center justify-center p-4 bg-neo-maroon">
          <NeoCard className="p-8 text-center max-w-md">
            <div className="w-20 h-20 bg-neo-cream border-[3px] border-neo-navy flex items-center justify-center mx-auto mb-6 rounded-full">
              <AlertCircle className="w-10 h-10 text-neo-maroon" />
            </div>
            <h2 className="text-3xl font-heading font-bold mb-2 text-neo-navy">Session Invalid</h2>
            <p className="text-neo-navy/70 mb-6 font-bold">
              {error || 'This report link is invalid or has expired.'}
            </p>
            <p className="text-sm text-neo-navy/60 mb-6">
              Please generate a new report link from WhatsApp.
            </p>
          </NeoCard>
        </div>
      </Layout>
    );
  }

  // Encrypting state
  if (status === 'encrypting') {
    return (
      <Layout>
        <div className="min-h-[80vh] flex items-center justify-center p-4 bg-neo-cream">
          <NeoCard className="p-12 text-center max-w-md">
            <div className="w-24 h-24 border-[4px] border-neo-orange border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
            <h2 className="text-2xl font-heading font-bold mb-2 text-neo-navy">{t('report.encryptingReport')}</h2>
            <p className="text-neo-navy/60">{t('report.encryptingInBrowser')}</p>
            <NeoCard variant="navy" className="mt-6 p-4">
              <code className="text-sm text-neo-orange font-mono">{t('report.naclInProgress')}</code>
            </NeoCard>
          </NeoCard>
        </div>
      </Layout>
    );
  }

  // Submitting state
  if (status === 'submitting') {
    return (
      <Layout>
        <div className="min-h-[80vh] flex items-center justify-center p-4 bg-neo-navy">
          <NeoCard variant="teal" className="p-12 text-center max-w-md">
            <div className="w-24 h-24 border-[4px] border-neo-orange border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
            <h2 className="text-2xl font-heading font-bold text-neo-cream mb-2">{t('report.submittingToBlockchain')}</h2>
            <p className="text-neo-cream/70">{t('report.storingOnIPFS')}</p>
            <div className="mt-8 space-y-3 text-left">
              <div className="flex items-center gap-3 text-neo-cream">
                <div className="w-8 h-8 bg-neo-orange border-[2px] border-neo-cream flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-neo-navy" />
                </div>
                <span className="font-bold">{t('report.encryptedLocally')}</span>
              </div>
              <div className="flex items-center gap-3 text-neo-cream animate-pulse">
                <div className="w-8 h-8 border-[2px] border-neo-cream flex items-center justify-center">
                  <div className="w-4 h-4 border-2 border-neo-orange border-t-transparent rounded-full animate-spin" />
                </div>
                <span className="font-bold">{t('report.uploadingToIPFS')}</span>
              </div>
              <div className="flex items-center gap-3 text-neo-cream/50">
                <div className="w-8 h-8 border-[2px] border-neo-cream/50 flex items-center justify-center">
                  <Zap className="w-5 h-5" />
                </div>
                <span>{t('report.recordingOnEthereum')}</span>
              </div>
            </div>
          </NeoCard>
        </div>
      </Layout>
    );
  }

  // Success state
  if (status === 'done') {
    return (
      <Layout>
        <div className="min-h-[80vh] flex items-center justify-center p-4 bg-neo-teal">
          <NeoCard className="p-8 text-center max-w-lg">
            <div className="w-20 h-20 bg-neo-orange border-[3px] border-neo-navy flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-10 h-10 text-neo-navy" />
            </div>
            <h2 className="text-3xl font-heading font-bold mb-2 text-neo-navy">{t('report.reportSubmitted')}</h2>
            <p className="text-neo-navy/70 mb-6">
              {t('report.reportStoredMessage')}
            </p>

            <NeoCard variant="navy" className="p-4 text-left space-y-3 mb-6">
              <div>
                <p className="text-xs uppercase font-bold text-neo-orange mb-1">{t('report.ipfsCid')}</p>
                <p className="text-sm font-mono text-neo-cream break-all mb-2">{result?.cid || 'N/A'}</p>
                {result?.cid && (
                  <a
                    href={`https://gateway.pinata.cloud/ipfs/${result.cid}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-neo-orange hover:underline flex items-center gap-1"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Verify on IPFS (Pinata Gateway)
                  </a>
                )}
              </div>
              <div className="neo-divider bg-neo-teal/30"></div>
              <div>
                <p className="text-xs uppercase font-bold text-neo-orange mb-1">{t('report.transactionHash')}</p>
                <p className="text-sm font-mono text-neo-cream break-all">{result?.txHash || 'N/A'}</p>
              </div>
              <div className="neo-divider bg-neo-teal/30"></div>
              <div>
                <p className="text-xs uppercase font-bold text-neo-orange mb-1">{t('report.reportId')}</p>
                <p className="text-sm font-mono text-neo-cream">{result?.reportId || 'N/A'}</p>
              </div>
            </NeoCard>

            <div className="space-y-3">
              <a
                href={`https://sepolia.etherscan.io/tx/${result?.txHash || '0x123'}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <NeoButton variant="orange" className="w-full">
                  {t('report.viewOnEtherscan')}
                  <ExternalLink className="w-4 h-4 ml-2" />
                </NeoButton>
              </a>
              <Link to="/reporter">
                <NeoButton variant="navy" className="w-full">
                  {t('report.backToDashboardBtn')}
                </NeoButton>
              </Link>
            </div>
          </NeoCard>
        </div>
      </Layout>
    );
  }

  // Main form
  return (
    <Layout>
      {/* Header Section */}
      <section className="bg-neo-navy py-8 border-b-[4px] border-neo-navy">
        <div className="container mx-auto px-4 max-w-4xl">
          <Link to="/reporter" className="inline-flex items-center gap-2 text-neo-cream/70 hover:text-neo-orange mb-4 transition-colors">
            <ArrowLeft className="w-4 h-4" />
            {t('report.backToDashboard')}
          </Link>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-4xl md:text-5xl font-heading font-bold text-neo-cream mb-2">{t('report.title')}</h1>
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                  <span className="neo-badge-orange">
                    <Lock className="w-3 h-3" />
                    {t('common.encrypted')}
                  </span>
                  <span className="text-sm text-neo-cream/50 font-mono">{t('common.session')}: {sessionId}</span>
                </div>
                {walletAddress && (
                  <div className="flex items-center gap-2 text-neo-teal text-sm font-mono">
                    <span>Reporting as:</span>
                    <span className="bg-neo-navy-light px-2 py-0.5 rounded border border-neo-teal/30 text-neo-cream">
                      {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
                    </span>
                  </div>
                )}
              </div>
            </div>
            <NeoCard className="p-3 bg-neo-teal border-neo-teal">
              <div className="flex items-center gap-2 text-neo-cream">
                <Shield className="w-5 h-5" />
                <span className="text-sm font-bold">{t('report.endToEndEncrypted')}</span>
              </div>
            </NeoCard>
          </div>
        </div>
      </section>

      {/* Form Section */}
      <section className="py-12 bg-neo-cream">
        <div className="container mx-auto px-4 max-w-4xl">
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Main Form */}
            <div className="lg:col-span-2">
              <NeoCard className="p-6 md:p-8">
                {/* Category */}
                <div className="mb-8">
                  <label className="block font-heading font-bold mb-4 text-neo-navy text-lg">
                    {t('report.crimeCategory')} <span className="text-neo-maroon">*</span>
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {crimeCategories.map((cat) => (
                      <button
                        key={cat.id}
                        onClick={() => setCategory(cat.id)}
                        className={`
                          p-4 border-[3px] border-neo-navy text-left transition-all
                          ${category === cat.id
                            ? 'bg-neo-orange shadow-none translate-x-[2px] translate-y-[2px]'
                            : 'bg-neo-cream shadow-neo hover:bg-neo-teal hover:text-neo-cream'
                          }
                        `}
                      >
                        <span className="text-2xl block mb-2">{cat.icon}</span>
                        <span className="text-xs font-bold uppercase leading-tight">{cat.label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Severity */}
                <div className="mb-8">
                  <label className="block font-heading font-bold mb-4 text-neo-navy text-lg">
                    {t('report.severityLevel')}
                  </label>
                  <NeoCard variant="navy" className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-neo-cream">{t('report.low')}</span>
                      <span className="text-4xl font-heading font-bold text-neo-orange">{severity}</span>
                      <span className="text-neo-cream">{t('report.critical')}</span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={severity}
                      onChange={(e) => setSeverity(Number(e.target.value))}
                      className="w-full h-4 bg-neo-teal appearance-none cursor-pointer
                                 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-8 [&::-webkit-slider-thumb]:h-8 
                                 [&::-webkit-slider-thumb]:bg-neo-orange [&::-webkit-slider-thumb]:border-[3px] [&::-webkit-slider-thumb]:border-neo-cream
                                 [&::-webkit-slider-thumb]:cursor-pointer"
                    />
                  </NeoCard>
                </div>

                {/* Report Text */}
                <div className="mb-8">
                  <label className="block font-heading font-bold mb-2 text-neo-navy text-lg">
                    {t('report.describeIncident')} <span className="text-neo-maroon">*</span>
                  </label>
                  <div className="flex items-center gap-2 text-neo-teal text-sm mb-3">
                    <Lock className="w-4 h-4" />
                    <span>{t('report.encryptionNote')}</span>
                  </div>
                  <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder={t('report.placeholder')}
                    className="neo-textarea h-48"
                    disabled={status === 'encrypting' || status === 'submitting'}
                  />
                </div>

                {/* File Upload */}
                <div className="mb-8">
                  <label className="block font-heading font-bold mb-3 text-neo-navy text-lg">
                    {t('report.evidence')} <span className="text-neo-navy/50 text-sm font-normal">{t('report.optional')}</span>
                  </label>
                  <div
                    className="border-[3px] border-dashed border-neo-navy p-8 text-center hover:bg-neo-teal/10 transition-colors cursor-pointer"
                    onDragOver={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                    onDragLeave={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      const droppedFiles = Array.from(e.dataTransfer.files);
                      handleFileSelection(droppedFiles);
                    }}
                  >
                    <Upload className="w-12 h-12 text-neo-teal mx-auto mb-4" />
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept="image/*,video/*,.pdf,.doc,.docx,.txt"
                      onChange={(e) => {
                        if (e.target.files && e.target.files.length > 0) {
                          handleFileSelection(Array.from(e.target.files));
                          // Reset input so same file can be selected again
                          e.target.value = '';
                        }
                      }}
                      className="hidden"
                      id="file-upload"
                      disabled={status === 'encrypting' || status === 'submitting'}
                    />
                    <div 
                      className="cursor-pointer" 
                      onClick={() => {
                        if (fileInputRef.current && status !== 'encrypting' && status !== 'submitting') {
                          fileInputRef.current.click();
                        }
                      }}
                    >
                      <NeoButton 
                        variant="teal" 
                        size="sm" 
                        type="button" 
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          if (fileInputRef.current && status !== 'encrypting' && status !== 'submitting') {
                            fileInputRef.current.click();
                          }
                        }}
                      >
                        {t('report.chooseFiles')}
                      </NeoButton>
                      <p className="text-sm text-neo-navy/60 mt-3">Images, videos, documents • Max 10MB each</p>
                    </div>
                    {files.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {files.map((file, index) => (
                          <NeoCard key={index} variant="orange" className="p-3 flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              <p className="font-bold text-neo-navy truncate">{file.name}</p>
                              <p className="text-xs text-neo-navy/70">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                            </div>
                            <button
                              onClick={() => {
                                const newFiles = files.filter((_, i) => i !== index);
                                setFiles(newFiles);
                              }}
                              className="ml-3 text-neo-maroon hover:text-neo-navy transition-colors"
                              type="button"
                              disabled={status === 'encrypting' || status === 'submitting'}
                              title="Remove file"
                            >
                              <X className="w-5 h-5" />
                            </button>
                          </NeoCard>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Error */}
                {error && (
                  <NeoCard className="p-4 mb-6 bg-neo-maroon border-neo-maroon">
                    <div className="flex items-center gap-2 text-neo-cream">
                      <AlertCircle className="w-5 h-5" />
                      <p className="font-bold">{error}</p>
                    </div>
                  </NeoCard>
                )}

                {/* Submit */}
                <NeoButton
                  onClick={handleSubmit}
                  variant="orange"
                  size="lg"
                  className="w-full"
                  disabled={!text.trim() || !category}
                >
                  <Lock className="w-5 h-5 mr-2" />
                  {t('report.encryptAndSubmit')}
                </NeoButton>
              </NeoCard>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Security Info */}
              <NeoCard variant="navy" className="p-5">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-neo-orange flex items-center justify-center">
                    <Shield className="w-5 h-5 text-neo-navy" />
                  </div>
                  <h3 className="font-heading font-bold text-neo-cream">{t('report.yourSafety')}</h3>
                </div>
                <ul className="space-y-3 text-sm text-neo-cream/80">
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-neo-orange flex-shrink-0 mt-0.5" />
                    <span>{t('report.safety1')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-neo-orange flex-shrink-0 mt-0.5" />
                    <span>{t('report.safety2')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-neo-orange flex-shrink-0 mt-0.5" />
                    <span>{t('report.safety3')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-neo-orange flex-shrink-0 mt-0.5" />
                    <span>{t('report.safety4')}</span>
                  </li>
                </ul>
              </NeoCard>

              {/* Rewards */}
              <NeoCard variant="teal" className="p-5">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-neo-orange flex items-center justify-center">
                    <Zap className="w-5 h-5 text-neo-navy" />
                  </div>
                  <h3 className="font-heading font-bold text-neo-cream">{t('report.earnRewards')}</h3>
                </div>
                <p className="text-sm text-neo-cream/80">
                  {t('report.earnRewardsDesc')}
                </p>
                <div className="mt-4 p-3 bg-neo-navy/30">
                  <p className="text-xs text-neo-cream/60 uppercase">{t('report.averageReward')}</p>
                  <p className="text-2xl font-heading font-bold text-neo-orange">0.005 ETH</p>
                </div>
              </NeoCard>

              {/* Tips */}
              <NeoCard className="p-5">
                <h3 className="font-heading font-bold text-neo-navy mb-3">{t('report.reportTips')}</h3>
                <ul className="space-y-2 text-sm text-neo-navy/70">
                  <li>• {t('report.tip1')}</li>
                  <li>• {t('report.tip2')}</li>
                  <li>• {t('report.tip3')}</li>
                  <li>• {t('report.tip4')}</li>
                  <li>• {t('report.tip5')}</li>
                </ul>
              </NeoCard>
            </div>
          </div>

          <p className="text-xs text-neo-navy/50 text-center mt-8 max-w-2xl mx-auto">
            {t('report.disclaimer')}
          </p>
        </div>
      </section>

      {/* Warning Modal */}
      {showWarning && (
        <div className="fixed inset-0 bg-neo-navy/90 flex items-center justify-center p-4 z-50">
          <NeoCard className="max-w-md w-full p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-14 h-14 bg-neo-orange border-[3px] border-neo-navy flex items-center justify-center">
                <AlertTriangle className="w-7 h-7 text-neo-navy" />
              </div>
              <div>
                <h3 className="text-xl font-heading font-bold text-neo-navy">{t('report.confirmSubmission')}</h3>
                <p className="text-sm text-neo-navy/60">{t('report.actionPermanent')}</p>
              </div>
            </div>
            <NeoCard variant="maroon" className="p-4 mb-6">
              <p className="text-neo-cream text-sm">
                {t('report.permanentWarning')}
              </p>
            </NeoCard>
            <div className="flex gap-3">
              <NeoButton
                variant="navy"
                className="flex-1"
                onClick={() => setShowWarning(false)}
              >
                {t('common.cancel')}
              </NeoButton>
              <NeoButton
                variant="orange"
                danger
                className="flex-1"
                onClick={confirmSubmit}
              >
                {t('report.submitReport')}
              </NeoButton>
            </div>
          </NeoCard>
        </div>
      )}
    </Layout>
  );
}
