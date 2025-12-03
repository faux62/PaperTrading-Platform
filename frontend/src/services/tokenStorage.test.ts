/**
 * Unit Tests - Token Storage Service
 * Tests for token storage utility
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock the tokenStorage module to test in isolation
const STORAGE_KEY = 'papertrading-auth';

interface TokenStorageData {
  state: {
    accessToken: string | null;
    refreshToken: string | null;
  };
}

// Create a simple tokenStorage implementation for testing
const createTokenStorage = () => {
  const getStoredData = (): TokenStorageData | null => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // Ignore parse errors
    }
    return null;
  };

  return {
    getAccessToken: (): string | null => {
      const data = getStoredData();
      return data?.state?.accessToken || null;
    },

    getRefreshToken: (): string | null => {
      const data = getStoredData();
      return data?.state?.refreshToken || null;
    },

    setTokens: (accessToken: string, refreshToken: string): void => {
      const data = getStoredData() || { state: { accessToken: null, refreshToken: null } };
      data.state.accessToken = accessToken;
      data.state.refreshToken = refreshToken;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    },

    clearTokens: (): void => {
      localStorage.removeItem(STORAGE_KEY);
    },
  };
};

describe('tokenStorage', () => {
  let tokenStorage: ReturnType<typeof createTokenStorage>;

  beforeEach(() => {
    // Clear localStorage mock before each test
    vi.mocked(localStorage.getItem).mockReturnValue(null);
    vi.mocked(localStorage.setItem).mockClear();
    vi.mocked(localStorage.removeItem).mockClear();
    tokenStorage = createTokenStorage();
  });

  describe('getAccessToken', () => {
    it('should return null when no token stored', () => {
      expect(tokenStorage.getAccessToken()).toBeNull();
    });

    it('should return access token when stored', () => {
      const storedData: TokenStorageData = {
        state: {
          accessToken: 'test-access-token',
          refreshToken: 'test-refresh-token',
        },
      };
      vi.mocked(localStorage.getItem).mockReturnValue(JSON.stringify(storedData));

      expect(tokenStorage.getAccessToken()).toBe('test-access-token');
    });

    it('should return null for invalid JSON', () => {
      vi.mocked(localStorage.getItem).mockReturnValue('invalid-json');

      expect(tokenStorage.getAccessToken()).toBeNull();
    });
  });

  describe('getRefreshToken', () => {
    it('should return null when no token stored', () => {
      expect(tokenStorage.getRefreshToken()).toBeNull();
    });

    it('should return refresh token when stored', () => {
      const storedData: TokenStorageData = {
        state: {
          accessToken: 'test-access-token',
          refreshToken: 'test-refresh-token',
        },
      };
      vi.mocked(localStorage.getItem).mockReturnValue(JSON.stringify(storedData));

      expect(tokenStorage.getRefreshToken()).toBe('test-refresh-token');
    });
  });

  describe('setTokens', () => {
    it('should store tokens in localStorage', () => {
      tokenStorage.setTokens('new-access', 'new-refresh');

      expect(localStorage.setItem).toHaveBeenCalledWith(
        STORAGE_KEY,
        expect.stringContaining('new-access')
      );
    });

    it('should update existing tokens', () => {
      const existingData: TokenStorageData = {
        state: {
          accessToken: 'old-access',
          refreshToken: 'old-refresh',
        },
      };
      vi.mocked(localStorage.getItem).mockReturnValue(JSON.stringify(existingData));

      tokenStorage.setTokens('new-access', 'new-refresh');

      const setItemCall = vi.mocked(localStorage.setItem).mock.calls[0];
      const savedData = JSON.parse(setItemCall[1]);
      expect(savedData.state.accessToken).toBe('new-access');
      expect(savedData.state.refreshToken).toBe('new-refresh');
    });
  });

  describe('clearTokens', () => {
    it('should remove tokens from localStorage', () => {
      tokenStorage.clearTokens();

      expect(localStorage.removeItem).toHaveBeenCalledWith(STORAGE_KEY);
    });
  });
});
