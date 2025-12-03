import { test, expect } from '@playwright/test';

/**
 * Dashboard E2E Tests
 * Tests for the main dashboard functionality.
 * 
 * NOTE: These tests require authenticated state.
 */

test.describe('Dashboard Page', () => {
  // TODO: Add authentication setup fixture
  test.skip('should load dashboard for authenticated user', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check main dashboard elements
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });

  test.skip('should display portfolio summary', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check for portfolio value display
    await expect(page.getByText(/total value|portfolio value/i)).toBeVisible();
  });

  test.skip('should display recent trades', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check for recent trades section
    await expect(page.getByText(/recent trades|trade history/i)).toBeVisible();
  });

  test.skip('should display watchlist', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check for watchlist section
    await expect(page.getByText(/watchlist/i)).toBeVisible();
  });

  test.skip('should display market overview', async ({ page }) => {
    await page.goto('/dashboard');
    
    // Check for market data
    await expect(page.getByText(/market|indices/i)).toBeVisible();
  });
});

test.describe('Dashboard Navigation', () => {
  test.skip('should navigate to portfolio from dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    
    await page.getByRole('link', { name: /portfolio/i }).click();
    await expect(page).toHaveURL(/portfolio/);
  });

  test.skip('should navigate to trading from dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    
    await page.getByRole('link', { name: /trading|trade/i }).click();
    await expect(page).toHaveURL(/trading/);
  });

  test.skip('should navigate to analytics from dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    
    await page.getByRole('link', { name: /analytics/i }).click();
    await expect(page).toHaveURL(/analytics/);
  });
});

test.describe('Dashboard Responsiveness', () => {
  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    
    // Page should load without horizontal scroll
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 10); // Small tolerance
  });

  test('should be responsive on tablet', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 10);
  });
});
