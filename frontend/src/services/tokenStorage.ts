/**
 * Token Storage
 * 
 * Centralized token storage to avoid circular dependencies
 * between api.ts and authStore.ts
 */

const STORAGE_KEY = 'papertrading-auth';

interface TokenData {
  accessToken: string | null;
  refreshToken: string | null;
}

// In-memory cache
let tokenCache: TokenData = {
  accessToken: null,
  refreshToken: null,
};

// Initialize from localStorage
const initFromStorage = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      tokenCache.accessToken = parsed.state?.accessToken || null;
      tokenCache.refreshToken = parsed.state?.refreshToken || null;
    }
  } catch {
    // Ignore errors
  }
};

// Initialize on load
initFromStorage();

export const tokenStorage = {
  getAccessToken: (): string | null => {
    // Re-read from storage in case it changed
    initFromStorage();
    return tokenCache.accessToken;
  },

  getRefreshToken: (): string | null => {
    initFromStorage();
    return tokenCache.refreshToken;
  },

  setTokens: (accessToken: string, refreshToken: string) => {
    tokenCache.accessToken = accessToken;
    tokenCache.refreshToken = refreshToken;
  },

  clearTokens: () => {
    tokenCache.accessToken = null;
    tokenCache.refreshToken = null;
  },
};

export default tokenStorage;
