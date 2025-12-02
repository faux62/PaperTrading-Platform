/**
 * PaperTrading Platform - Auth Store
 * Zustand store for authentication state
 */
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User } from '../types';
import { authApi } from '../services/api';
import { tokenStorage } from '../services/tokenStorage';

interface AuthState {
  // State
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  setUser: (user: User | null) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  
  // Async actions
  login: (email: string, password: string) => Promise<boolean>;
  register: (username: string, email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Setters
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setTokens: (accessToken, refreshToken) => {
        // Sync with tokenStorage for api interceptors
        tokenStorage.setTokens(accessToken, refreshToken);
        set({ accessToken, refreshToken, isAuthenticated: true });
      },
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),

      // Login
      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const data = await authApi.login(email, password);
          set({
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
          // Fetch user profile
          await get().fetchUser();
          return true;
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Login failed',
            isLoading: false,
            isAuthenticated: false,
          });
          return false;
        }
      },

      // Register
      register: async (username, email, password) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.register({
            username,
            email,
            password,
          });
          set({
            user: {
              id: response.id,
              email: response.email,
              username: response.username,
              full_name: response.full_name,
              is_active: response.is_active,
              is_superuser: response.is_superuser,
              created_at: response.created_at,
              updated_at: response.updated_at,
            },
            accessToken: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
          return true;
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Registration failed',
            isLoading: false,
          });
          return false;
        }
      },

      // Logout
      logout: async () => {
        try {
          await authApi.logout();
        } catch {
          // Continue logout even if API call fails
        } finally {
          // Clear token storage
          tokenStorage.clearTokens();
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            error: null,
          });
        }
      },

      // Fetch user profile
      fetchUser: async () => {
        const { accessToken } = get();
        if (!accessToken) return;

        try {
          const user = await authApi.getMe();
          set({ user });
        } catch (error) {
          // Token might be invalid
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
          });
        }
      },

      // Check if still authenticated
      checkAuth: async () => {
        const { accessToken, refreshToken } = get();
        if (!accessToken) return false;

        try {
          await get().fetchUser();
          return get().isAuthenticated;
        } catch {
          if (refreshToken) {
            // Try to refresh token
            try {
              const response = await authApi.login(refreshToken, ''); // This will use interceptor
              set({
                accessToken: response.access_token,
                refreshToken: response.refresh_token,
              });
              return true;
            } catch {
              return false;
            }
          }
          return false;
        }
      },
    }),
    {
      name: 'papertrading-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
