import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { createSession as apiCreateSession } from '../lib/api';

const SessionContext = createContext(null);

const STORAGE_KEY = 'sayless_session';

export function SessionProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load session from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Check if session is still valid (not expired)
        if (parsed.expiresAt && new Date(parsed.expiresAt) > new Date()) {
          setSession(parsed);
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      }
    } catch (e) {
      console.error('Failed to load session from storage:', e);
      localStorage.removeItem(STORAGE_KEY);
    }
    setLoading(false);
  }, []);

  // Save session to localStorage when it changes
  useEffect(() => {
    if (session) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
      // Also save wallet address separately for backward compatibility
      if (session.walletAddress) {
        localStorage.setItem('walletAddress', session.walletAddress);
      }
    }
  }, [session]);

  // Create a new session via API
  const createNewSession = async (walletAddress) => {
    try {
      const response = await apiCreateSession(walletAddress);
      if (response.sessionId) {
        const newSession = {
          sessionId: response.sessionId,
          walletAddress: response.wallet || walletAddress,
          expiresAt: response.expiresAt
        };
        setSession(newSession);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newSession));
        if (newSession.walletAddress) {
          localStorage.setItem('walletAddress', newSession.walletAddress);
        }
        return newSession;
      }
      return null;
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    }
  };

  // Save session from backend validation (used when clicking Twilio link)
  // Memoized with useCallback to prevent infinite loops in components that depend on it
  const saveSession = useCallback((sessionId, walletAddress, expiresAt = null) => {
    const newSession = {
      sessionId,
      walletAddress,
      expiresAt: expiresAt || new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() // 24 hours default
    };
    setSession(newSession);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newSession));
    if (walletAddress) {
      localStorage.setItem('walletAddress', walletAddress);
    }
    return newSession;
  }, []); // Empty deps - function doesn't depend on any state

  // Clear session
  const clearSession = () => {
    setSession(null);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem('walletAddress');
  };

  // Get wallet address (from session or localStorage)
  const getWalletAddress = () => {
    return session?.walletAddress || localStorage.getItem('walletAddress');
  };

  return (
    <SessionContext.Provider value={{
      session,
      loading,
      createNewSession,
      saveSession,
      clearSession,
      getWalletAddress,
      sessionId: session?.sessionId,
      walletAddress: session?.walletAddress || localStorage.getItem('walletAddress')
    }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}
