import { test, expect } from '@playwright/test';

/**
 * Trading Flow E2E Tests
 * Tests for order submission and trading functionality.
 * 
 * NOTE: These tests require authenticated state and working backend.
 */

test.describe('Trading Page', () => {
  test.skip('should display order form', async ({ page }) => {
    await page.goto('/trading');
    
    // Check order form elements
    await expect(page.getByLabel(/symbol/i)).toBeVisible();
    await expect(page.getByLabel(/quantity/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /buy/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /sell/i })).toBeVisible();
  });

  test.skip('should search for symbols', async ({ page }) => {
    await page.goto('/trading');
    
    // Type in symbol search
    await page.getByLabel(/symbol/i).fill('AAPL');
    
    // Should show autocomplete suggestions
    await expect(page.getByText(/Apple Inc/i)).toBeVisible({ timeout: 5000 });
  });

  test.skip('should display current positions', async ({ page }) => {
    await page.goto('/trading');
    
    // Check positions table
    await expect(page.getByRole('table')).toBeVisible();
    await expect(page.getByText(/positions|holdings/i)).toBeVisible();
  });

  test.skip('should show order types', async ({ page }) => {
    await page.goto('/trading');
    
    // Check order type selector
    const orderTypeSelect = page.getByLabel(/order type/i);
    await orderTypeSelect.click();
    
    await expect(page.getByText(/market/i)).toBeVisible();
    await expect(page.getByText(/limit/i)).toBeVisible();
  });
});

test.describe('Order Submission', () => {
  test.skip('should validate quantity is positive', async ({ page }) => {
    await page.goto('/trading');
    
    await page.getByLabel(/symbol/i).fill('AAPL');
    await page.getByLabel(/quantity/i).fill('-10');
    await page.getByRole('button', { name: /buy/i }).click();
    
    // Should show validation error
    await expect(page.getByText(/positive|greater than 0/i)).toBeVisible();
  });

  test.skip('should validate symbol is required', async ({ page }) => {
    await page.goto('/trading');
    
    await page.getByLabel(/quantity/i).fill('100');
    await page.getByRole('button', { name: /buy/i }).click();
    
    // Should show validation error
    await expect(page.getByText(/required|select a symbol/i)).toBeVisible();
  });

  test.skip('should submit market buy order', async ({ page }) => {
    await page.goto('/trading');
    
    // Fill order form
    await page.getByLabel(/symbol/i).fill('AAPL');
    await page.getByLabel(/quantity/i).fill('10');
    
    // Select market order
    await page.getByLabel(/order type/i).selectOption('market');
    
    // Submit buy order
    await page.getByRole('button', { name: /buy/i }).click();
    
    // Should show confirmation or success
    await expect(page.getByText(/submitted|success|confirmed/i)).toBeVisible({ timeout: 10000 });
  });

  test.skip('should require price for limit orders', async ({ page }) => {
    await page.goto('/trading');
    
    await page.getByLabel(/symbol/i).fill('AAPL');
    await page.getByLabel(/quantity/i).fill('10');
    await page.getByLabel(/order type/i).selectOption('limit');
    
    // Don't fill price
    await page.getByRole('button', { name: /buy/i }).click();
    
    // Should show validation error for price
    await expect(page.getByText(/price.*required/i)).toBeVisible();
  });
});

test.describe('Order History', () => {
  test.skip('should display order history', async ({ page }) => {
    await page.goto('/trading');
    
    // Navigate to order history
    await page.getByRole('tab', { name: /orders|history/i }).click();
    
    // Should show orders table
    await expect(page.getByRole('table')).toBeVisible();
  });

  test.skip('should allow canceling pending orders', async ({ page }) => {
    await page.goto('/trading');
    
    await page.getByRole('tab', { name: /orders|history/i }).click();
    
    // Find cancel button for pending order
    const cancelButton = page.getByRole('button', { name: /cancel/i }).first();
    
    if (await cancelButton.isVisible()) {
      await cancelButton.click();
      
      // Confirm cancellation
      await page.getByRole('button', { name: /confirm|yes/i }).click();
      
      // Should show cancellation confirmation
      await expect(page.getByText(/cancelled/i)).toBeVisible();
    }
  });
});
