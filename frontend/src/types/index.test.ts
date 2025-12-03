/**
 * Unit Tests - Type Guards and Validation
 * Tests for type validation utilities
 */
import { describe, it, expect } from 'vitest';
import type { User, Portfolio, Position, Trade, RiskProfile } from './index';

// Type guard functions for testing
const isValidUser = (data: unknown): data is User => {
  if (!data || typeof data !== 'object') return false;
  const user = data as Record<string, unknown>;
  return (
    typeof user.id === 'number' &&
    typeof user.email === 'string' &&
    typeof user.username === 'string' &&
    typeof user.is_active === 'boolean'
  );
};

const isValidPortfolio = (data: unknown): data is Portfolio => {
  if (!data || typeof data !== 'object') return false;
  const portfolio = data as Record<string, unknown>;
  return (
    typeof portfolio.id === 'number' &&
    typeof portfolio.name === 'string' &&
    typeof portfolio.initial_capital === 'number' &&
    ['aggressive', 'balanced', 'conservative'].includes(portfolio.risk_profile as string)
  );
};

const isValidRiskProfile = (value: unknown): value is RiskProfile => {
  return ['aggressive', 'balanced', 'conservative'].includes(value as string);
};

describe('Type Guards', () => {
  describe('isValidUser', () => {
    it('should return true for valid user object', () => {
      const validUser = {
        id: 1,
        email: 'test@example.com',
        username: 'testuser',
        full_name: 'Test User',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };
      expect(isValidUser(validUser)).toBe(true);
    });

    it('should return false for missing required fields', () => {
      const invalidUser = {
        id: 1,
        email: 'test@example.com',
        // missing username
      };
      expect(isValidUser(invalidUser)).toBe(false);
    });

    it('should return false for wrong types', () => {
      const invalidUser = {
        id: '1', // should be number
        email: 'test@example.com',
        username: 'testuser',
        is_active: true,
      };
      expect(isValidUser(invalidUser)).toBe(false);
    });

    it('should return false for null', () => {
      expect(isValidUser(null)).toBe(false);
    });

    it('should return false for undefined', () => {
      expect(isValidUser(undefined)).toBe(false);
    });
  });

  describe('isValidPortfolio', () => {
    it('should return true for valid portfolio', () => {
      const validPortfolio = {
        id: 1,
        user_id: 1,
        name: 'My Portfolio',
        description: 'Test portfolio',
        initial_capital: 100000,
        current_value: 105000,
        cash_balance: 50000,
        risk_profile: 'balanced',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };
      expect(isValidPortfolio(validPortfolio)).toBe(true);
    });

    it('should return false for invalid risk profile', () => {
      const invalidPortfolio = {
        id: 1,
        name: 'My Portfolio',
        initial_capital: 100000,
        risk_profile: 'invalid_profile',
      };
      expect(isValidPortfolio(invalidPortfolio)).toBe(false);
    });
  });

  describe('isValidRiskProfile', () => {
    it('should return true for aggressive', () => {
      expect(isValidRiskProfile('aggressive')).toBe(true);
    });

    it('should return true for balanced', () => {
      expect(isValidRiskProfile('balanced')).toBe(true);
    });

    it('should return true for conservative', () => {
      expect(isValidRiskProfile('conservative')).toBe(true);
    });

    it('should return false for invalid value', () => {
      expect(isValidRiskProfile('risky')).toBe(false);
    });

    it('should return false for non-string', () => {
      expect(isValidRiskProfile(123)).toBe(false);
    });
  });
});

describe('Type Definitions', () => {
  describe('User type', () => {
    it('should allow valid user creation', () => {
      const user: User = {
        id: 1,
        email: 'test@example.com',
        username: 'testuser',
        full_name: 'Test User',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };
      expect(user.id).toBe(1);
    });

    it('should allow null full_name', () => {
      const user: User = {
        id: 1,
        email: 'test@example.com',
        username: 'testuser',
        full_name: null,
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };
      expect(user.full_name).toBeNull();
    });
  });

  describe('Portfolio type', () => {
    it('should accept all risk profiles', () => {
      const profiles: RiskProfile[] = ['aggressive', 'balanced', 'conservative'];
      profiles.forEach((profile) => {
        const portfolio: Partial<Portfolio> = { risk_profile: profile };
        expect(['aggressive', 'balanced', 'conservative']).toContain(portfolio.risk_profile);
      });
    });
  });
});
