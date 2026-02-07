const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

export async function checkSession(sessionId) {
  const response = await fetch(`${API_URL}/api/session/${sessionId}`);
  return response.json();
}

export async function submitReport(sessionId, payload) {
  const response = await fetch(`${API_URL}/api/report`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ sessionId, payload })
  });
  return response.json();
}

export async function getAuthorityReports() {
  const response = await fetch(`${API_URL}/api/authority/reports`);
  return response.json();
}

export async function decryptReport(reportId) {
  const response = await fetch(`${API_URL}/api/authority/decrypt/${reportId}`, {
    method: 'POST'
  });
  return response.json();
}

export async function verifyReport(reportId, rewardAmount = '0.005') {
  const response = await fetch(`${API_URL}/api/authority/verify/${reportId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ rewardAmount })
  });
  return response.json();
}

export async function rejectReport(reportId) {
  const response = await fetch(`${API_URL}/api/authority/reject/${reportId}`, {
    method: 'POST'
  });
  return response.json();
}

export async function getAuthorityStats() {
  const response = await fetch(`${API_URL}/api/authority/stats`);
  return response.json();
}

// Reporter API functions
export async function createSession(walletAddress) {
  const response = await fetch(`${API_URL}/api/reporter/session`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ walletAddress })
  });
  return response.json();
}

export async function getReporterStats(walletAddress) {
  const response = await fetch(`${API_URL}/api/reporter/stats/${walletAddress}`);
  return response.json();
}

export async function getReporterReports(walletAddress, limit = 10) {
  const response = await fetch(`${API_URL}/api/reporter/reports/${walletAddress}?limit=${limit}`);
  return response.json();
}

// export async function getReputationData(walletAddress) {
//   const response = await fetch(`${API_URL}/api/reporter/reputation/${walletAddress}`);
//   return response.json();
// }

export async function getWalletData(walletAddress) {
  const response = await fetch(`${API_URL}/api/reporter/wallet/${walletAddress}`);
  return response.json();
}

export async function claimRewards(walletAddress) {
  const response = await fetch(`${API_URL}/api/reporter/claim-rewards`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ walletAddress })
  });
  return response.json();
}

// Jury API functions
export async function getJuryReports() {
  const response = await fetch(`${API_URL}/api/jury/cases`);
  return response.json();
}

export async function submitJuryVote(reportId, vote, walletAddress) {
  const response = await fetch(`${API_URL}/api/jury/vote/${reportId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ vote, walletAddress })
  });
  return response.json();
}

export async function getJuryStats(walletAddress) {
  const response = await fetch(`${API_URL}/api/jury/stats/${walletAddress}`);
  return response.json();
}

export async function getUserJuryVotes(walletAddress) {
  const response = await fetch(`${API_URL}/api/jury/user-votes/${walletAddress}`);
  return response.json();
}

export async function getReputationData(walletAddress) {
  const response = await fetch(`${API_URL}/api/reputation/${walletAddress}`);
  return response.json();
}

// ============================================================
// Business Analytics API
// ============================================================

const ANALYTICS_API_URL = import.meta.env.VITE_ANALYTICS_API_URL || 'http://localhost:8000/api/v1';

export async function calculateAnalytics(data) {
  const response = await fetch(`${ANALYTICS_API_URL}/analytics/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Calculation failed' }));
    let message = 'Calculation failed';
    if (Array.isArray(err.detail)) {
      message = err.detail.map(e => `${(e.loc || []).slice(1).join('.')}: ${e.msg}`).join('; ');
    } else if (typeof err.detail === 'string') {
      message = err.detail;
    }
    throw new Error(message);
  }
  return response.json();
}

export async function simulateAnalytics(data) {
  const response = await fetch(`${ANALYTICS_API_URL}/analytics/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Simulation failed' }));
    let message = 'Simulation failed';
    if (Array.isArray(err.detail)) {
      message = err.detail.map(e => `${(e.loc || []).slice(1).join('.')}: ${e.msg}`).join('; ');
    } else if (typeof err.detail === 'string') {
      message = err.detail;
    }
    throw new Error(message);
  }
  return response.json();
}

export async function getCompetitiveAnalysis(data) {
  const response = await fetch(`${ANALYTICS_API_URL}/analytics/competitive-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Competitive analysis failed' }));
    let message = 'Competitive analysis failed';
    if (Array.isArray(err.detail)) {
      message = err.detail.map(e => `${(e.loc || []).slice(1).join('.')}: ${e.msg}`).join('; ');
    } else if (typeof err.detail === 'string') {
      message = err.detail;
    }
    throw new Error(message);
  }
  return response.json();
}

export async function getAnalyticsHealth() {
  const response = await fetch(`${ANALYTICS_API_URL}/analytics/health`);
  return response.json();
}

export async function getAnalyticsSchema() {
  const response = await fetch(`${ANALYTICS_API_URL}/analytics/schema`);
  return response.json();
}

