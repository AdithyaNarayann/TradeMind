// English translations
const en = {
    // Common
    common: {
        home: 'Home',
        reporter: 'Reporter',
        authority: 'Authority',
        jury: 'Jury',
        wallet: 'Wallet',
        back: 'Back',
        cancel: 'Cancel',
        submit: 'Submit',
        reset: 'Reset',
        close: 'Close',
        loading: 'Loading...',
        verified: 'Verified',
        pending: 'Pending',
        rejected: 'Rejected',
        session: 'Session',
        encrypted: 'Encrypted',
        reports: 'Reports',
        stakeUsed: 'Stake Used',
        reputation: 'Reputation',
        pendingRewards: 'Pending Rewards',
    },

    // Language Selection Modal
    languageModal: {
        title: 'Choose Your Language',
        subtitle: 'Select your preferred language for the application',
        english: 'English',
        hindi: 'हिंदी (Hindi)',
        continue: 'Continue',
    },

    // Navbar
    navbar: {
        home: 'Home',
        reporter: 'Reporter',
        authority: 'Authority',
        jury: 'Jury',
        wallet: 'Wallet',
    },

    // Landing Page
    landing: {
        badge: 'End-to-End Encrypted',
        sayLess: 'SAY LESS',
        tagline: 'Report Without Speaking',
        description: 'The anonymous crime reporting protocol. Your report is encrypted in your browser before it ever leaves your device.',
        evenWeCantRead: 'Even we cannot read it.',
        startReporting: 'Start Reporting',
        whatsApp: 'WhatsApp',
        secureReport: 'SECURE REPORT',

        // Stats
        stats: {
            anonymous: 'Anonymous',
            encrypted: 'Encrypted',
            available: 'Available',
            zeroData: 'Data Stored',
        },

        // Role Cards
        roleCards: {
            chooseYourPath: 'Choose Your Path',
            threeRolesOneMission: 'Three Roles, One Mission',
            enterDashboard: 'Enter Dashboard',
            reporter: {
                title: 'Reporter',
                description: 'Submit anonymous crime reports with full encryption. Your identity is protected by cryptography.',
            },
            authority: {
                title: 'Authority',
                description: 'Review and verify encrypted reports. Decrypt content securely and take action.',
            },
            jury: {
                title: 'Jury',
                description: 'Participate in dispute resolution. Vote on contested reports using reputation-weighted governance.',
            },
        },

        // Features Section
        features: {
            securityFirst: 'Security First',
            builtForZeroTrust: 'Built for Zero Trust',
            privacyPriority: 'Every layer of SAYLESS is designed with your privacy as the top priority.',
            clientSideEncryption: 'Client-Side Encryption',
            clientSideEncryptionDesc: 'Reports are encrypted using NaCl cryptography in your browser before transmission.',
            sessionBasedIdentity: 'Session-Based Identity',
            sessionBasedIdentityDesc: 'No accounts, no logins. Each session generates a unique, untraceable identifier.',
            ipfsBlockchain: 'IPFS + Blockchain',
            ipfsBlockchainDesc: 'Encrypted data stored on IPFS. Proof of existence recorded on Ethereum.',
            authorityOnlyDecryption: 'Authority-Only Decryption',
            authorityOnlyDecryptionDesc: 'Only designated authorities hold the keys to decrypt submitted reports.',
        },

        // How it Works
        howItWorks: {
            simpleProcess: 'Simple Process',
            title: 'How It Works',
            step1Title: 'Send "REPORT" on WhatsApp',
            step1Desc: 'Message our WhatsApp number. Receive a secure, one-time link instantly.',
            step2Title: 'Write Your Report',
            step2Desc: 'Open the link. Describe the incident. Everything encrypts before leaving your device.',
            step3Title: 'Stored Securely',
            step3Desc: 'Encrypted report goes to IPFS. Cryptographic proof recorded on Ethereum blockchain.',
            step4Title: 'Get Rewarded',
            step4Desc: 'Verified reports earn ETH rewards to your anonymous wallet.',
        },

        // CTA Section
        cta: {
            readyToReport: 'Ready to Report?',
            safetyPriority: 'Your safety is our priority. Start your anonymous report now.',
            createAnonymousReport: 'Create Anonymous Report',
            authorityLogin: 'Authority Login',
        },
    },

    // Reporter Home
    reporterHome: {
        title: 'Reporter Dashboard',
        subtitle: 'Your anonymous identity. Submit reports and earn rewards.',
        quickActions: 'Quick Actions',

        // Cards
        createReport: {
            title: 'Create Report',
            description: 'Submit an encrypted crime report with evidence',
            action: 'Start Now',
        },
        silentReport: {
            title: 'Silent Report',
            description: 'Morse-code style tap reporting for emergencies',
            action: 'Start Now',
        },
        myReputation: {
            title: 'My Reputation',
            description: 'View your anonymous identity and score',
            action: 'View Profile',
        },
        rewards: {
            title: 'Rewards',
            description: 'Check earnings and claim pending rewards',
            action: 'View Wallet',
        },

        // Recent Reports
        recentReports: 'Recent Reports',
        viewAllReports: 'View All Reports →',
        category: 'Category',

        // Quick Tips
        earnMore: 'Earn More',
        tip1: 'Higher severity = higher rewards',
        tip2: 'Include evidence for verification',
        tip3: 'Build reputation for weight bonuses',

        // Privacy Banner
        privacyProtected: 'Your Privacy is Protected',
        privacyMessage: 'Your session ID is temporary and cannot be linked to your real identity. All reports are encrypted end-to-end in your browser before transmission. Even we cannot read your reports.',
    },

    // Report Page
    report: {
        title: 'Create Report',
        backToDashboard: 'Back to Dashboard',
        endToEndEncrypted: 'End-to-End Encrypted',

        // Categories
        crimeCategory: 'Crime Category',
        categories: {
            theft: 'Theft / Robbery',
            assault: 'Assault / Violence',
            fraud: 'Fraud / Scam',
            corruption: 'Corruption / Bribery',
            harassment: 'Harassment',
            drugs: 'Drug-related',
            cybercrime: 'Cybercrime',
            other: 'Other',
        },

        // Severity
        severityLevel: 'Severity Level',
        low: 'Low',
        critical: 'Critical',

        // Description
        describeIncident: 'Describe the Incident',
        encryptionNote: 'This content will be encrypted before leaving your device',
        placeholder: 'Provide as much detail as possible about the incident. Include dates, locations, descriptions of people involved, and any other relevant information...',

        // Evidence
        evidence: 'Evidence',
        optional: '(optional)',
        chooseFiles: 'Choose Files',
        filesNote: 'Images, videos, documents • Max 10MB each',
        filesSelected: 'file(s) selected',

        // Errors
        selectCategoryAndEnter: 'Please select a category and enter your report',

        // Submit
        encryptAndSubmit: 'Encrypt & Submit Report',

        // Sidebar
        yourSafety: 'Your Safety',
        safety1: 'Report encrypted in browser',
        safety2: 'No personally identifiable data',
        safety3: 'Stored on decentralized IPFS',
        safety4: 'Only authorities can decrypt',

        earnRewards: 'Earn Rewards',
        earnRewardsDesc: 'Verified reports earn ETH rewards. Higher severity + detailed evidence = higher rewards.',
        averageReward: 'Average Reward',

        reportTips: 'Report Tips',
        tip1: 'Be specific with dates and times',
        tip2: 'Include location details',
        tip3: 'Describe suspects if known',
        tip4: 'Attach evidence if available',
        tip5: 'Review before submitting',

        disclaimer: 'By submitting, you confirm this is a genuine report. False reports will result in reputation penalties and stake slashing.',

        // Modal
        confirmSubmission: 'Confirm Submission',
        actionPermanent: 'This action is permanent',
        permanentWarning: 'Once submitted, your report cannot be modified or deleted. It will be permanently stored on the blockchain.',
        submitReport: 'Submit Report',

        // States
        encryptingReport: 'Encrypting Report...',
        encryptingInBrowser: 'Your report is being encrypted in this browser',
        naclInProgress: '🔐 NaCl encryption in progress...',

        submittingToBlockchain: 'Submitting to Blockchain...',
        storingOnIPFS: 'Storing on IPFS & recording proof on Ethereum',
        encryptedLocally: 'Encrypted locally',
        uploadingToIPFS: 'Uploading to IPFS...',
        recordingOnEthereum: 'Recording on Ethereum',

        reportSubmitted: 'Report Submitted!',
        reportStoredMessage: 'Your encrypted report has been stored on IPFS and verified on blockchain.',
        ipfsCid: 'IPFS CID',
        transactionHash: 'Transaction Hash',
        reportId: 'Report ID',
        viewOnEtherscan: 'View on Etherscan',
        backToDashboardBtn: 'Back to Dashboard',
    },

    // Silent Report
    silentReport: {
        title: 'Silent Report',
        subtitle: 'Tap to report without typing',
        backToDashboard: 'Back to Dashboard',
        howItWorks: 'How It Works',
        shortTap: 'Short tap (<0.5s)',
        longTap: 'Long tap (>0.5s)',
        quickCodes: 'Quick Codes:',
        patterns: {
            theft: 'Theft',
            assault: 'Assault',
            fraud: 'Fraud',
            harassment: 'Harassment',
            emergency: 'Emergency',
        },
        tapZone: 'Tap Zone',
        holding: 'HOLDING...',
        tapHere: 'TAP HERE',
        yourPattern: 'Your Pattern',
        waitingForTaps: 'Waiting for taps...',
        decodedResult: 'Decoded Result',
        category: 'Category',
        severity: 'Severity',
        notDetected: 'Not detected',
        submitSilentReport: 'Submit Silent Report',
        silentReportSent: 'Silent Report Sent!',
        transmitted: 'Your {category} has been transmitted silently.',
        pattern: 'Pattern:',
    },

    // Authority Dashboard
    authority: {
        badge: 'Authority Access',
        title: 'Authority Dashboard',
        subtitle: 'Review and verify encrypted crime reports',
        refresh: 'Refresh',
        totalReports: 'Total Reports',
        pendingReview: 'Pending Review',
        verified: 'Verified',
        rejected: 'Rejected',
        reports: 'Reports',
        reportDetails: 'Report Details',
        selectReportToDecrypt: 'Select a report to decrypt and review',
        decrypting: 'Decrypting with authority key...',
        decryptionFailed: 'Decryption failed:',
        decryptedReport: 'Decrypted Report',
        aiAnalysis: 'AI Analysis (Gemini)',
        spam: 'Spam',
        urgency: 'Urgency',
        category: 'Category',
        credibility: 'Credibility',
        suggestedAction: 'Suggested Action',
        verifyAndReward: 'Verify & Reward',
        reject: 'Reject',
        reportVerifiedRewarded: 'This report has been verified and rewarded.',
        reportRejected: 'This report has been rejected.',
        loadingReports: 'Loading reports...',
        noReportsFound: 'No reports found',
        status: {
            underReview: 'Under Review',
            verified: 'Verified',
            rejected: 'Rejected',
            pending: 'Pending',
        },
        filterAll: 'All',
        filterReview: 'Review',
    },

    // Jury Dashboard
    jury: {
        badge: 'Dispute Resolution',
        title: 'Jury Dashboard',
        subtitle: 'Vote on disputed reports. Your influence is weighted by reputation.',
        yourRep: 'Your Rep',
        voteWeight: 'Vote Weight',
        casesJudged: 'Cases Judged',
        successRate: 'Success Rate',
        allDisputes: 'All Disputes',
        active: 'Active',
        ended: 'Ended',
        categorySeverity: 'Category / Severity',
        reportSummary: 'Report Summary',
        reporterRep: 'Reporter Rep:',
        authorityRejection: "Authority's Rejection",
        reporterAppeal: "Reporter's Appeal",
        valid: 'Valid',
        invalid: 'Invalid',
        voters: 'voters',
        verdict: 'Verdict:',
        reportValid: 'Report Valid',
        reportInvalid: 'Report Invalid',
        youVoted: 'You voted:',
        voteValid: 'Vote Valid',
        voteInvalid: 'Vote Invalid',
        reputationWeightedVoting: 'Reputation-Weighted Voting',
        votingExplanation: 'Your vote is weighted by your reputation score. Higher reputation = more influence on the outcome. Voting correctly on disputes increases your reputation and earns rewards.',
    },

    // Wallet Dashboard
    wallet: {
        badge: 'Anonymous Wallet',
        title: 'Wallet Dashboard',
        subtitle: 'Stake reports and claim your rewards',
        address: 'Address',
        ethBalance: 'ETH Balance',
        usdcBalance: 'USDC Balance',
        pendingRewards: 'Pending Rewards',
        staked: 'Staked',
        stakeEth: 'Stake ETH',
        claimRewards: 'Claim Rewards',
        exportKey: 'Export Key',
        transactionHistory: 'Transaction History',
        reportVerified: 'Report Verified',
        reportStake: 'Report Stake',
        juryReward: 'Jury Reward',
        viewAllTransactions: 'View All Transactions →',
        totalValue: 'Total Value',
        change24h: '24h Change',
        staking: 'Staking',
        currentlyStaked: 'Currently Staked',
        pendingReportsCount: 'Pending Reports',
        estReturns: 'Est. Returns',
        security: 'Security',
        securityNote: 'This is a custodial wallet managed by SAYLESS. You can export your private key at any time. All transactions are on Ethereum Sepolia testnet.',
    },

    // Reputation Page
    reputation: {
        title: 'Reputation Profile',
        subtitle: 'Your pseudonymous identity on SAYLESS. Build reputation through verified reports.',
        anonymousIdentity: 'Anonymous Identity',
        reputationScore: 'Reputation Score',
        howItWorks: 'How Reputation Works',
        verifiedReports: 'Verified reports:',
        rejectedReports: 'Rejected reports:',
        correctJuryVotes: 'Correct jury votes:',
        wrongJuryVotes: 'Wrong jury votes:',
        higherRepHigherWeight: 'Higher reputation = Higher vote weight in jury',
        reportStatistics: 'Report Statistics',
        totalReports: 'Total Reports',
        accepted: 'Accepted',
        rejected: 'Rejected',
        acceptanceRate: 'Acceptance Rate',
        juryParticipation: 'Jury Participation',
        totalVotes: 'Total Votes',
        correct: 'Correct',
        incorrect: 'Incorrect',
        voteAccuracy: 'Vote Accuracy',
        rewardsEarned: 'Rewards Earned',
        penalties: 'Penalties',
        recentActivity: 'Recent Activity',
        tiers: {
            newcomer: 'Newcomer',
            regular: 'Regular',
            trusted: 'Trusted',
            expert: 'Expert',
            guardian: 'Guardian',
        },
    },

    // Footer
    footer: {
        description: 'Anonymous crime reporting protocol. Your reports are encrypted and cannot be traced back to you.',
        quickLinks: 'Quick Links',
        startReporting: '→ Start Reporting',
        authorityDashboard: '→ Authority Dashboard',
        checkReputation: '→ Check Reputation',
        disclaimer: 'Disclaimer',
        disclaimerText: 'This is a frontend-only demo for Project VEIL. No actual blockchain transactions or data storage occurs. All data is mocked using local state.',
        copyright: '© 2026 SAYLESS Protocol • Built for Project VEIL',
    },

    // Alert Banner
    alertBanner: {
        message: '⚠️ EVEN WE CANNOT READ YOUR REPORTS • FULLY ENCRYPTED • ANONYMOUS BY DESIGN • ',
    },
};

export default en;
