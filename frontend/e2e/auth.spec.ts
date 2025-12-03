import { test, expect } from '@playwright/test';

/**
 * Authentication E2E Tests
 * Tests for login, logout, and registration flows.
 * 
 * NOTE: These tests require:
 * - Frontend running on localhost:5173
 * - Backend running on localhost:8000
 * - Test user in database
 */

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Start from the login page
    await page.goto('/login');
  });

  test('should display login form', async ({ page }) => {
    // Check login form elements exist
    await expect(page.getByRole('heading', { name: /login|sign in/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /login|sign in/i })).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    // Fill in invalid credentials
    await page.getByLabel(/email/i).fill('invalid@example.com');
    await page.getByLabel(/password/i).fill('wrongpassword');
    
    // Submit the form
    await page.getByRole('button', { name: /login|sign in/i }).click();
    
    // Should show error message
    await expect(page.getByText(/invalid|incorrect|error/i)).toBeVisible({ timeout: 5000 });
  });

  test('should show validation error for empty fields', async ({ page }) => {
    // Click login without filling fields
    await page.getByRole('button', { name: /login|sign in/i }).click();
    
    // Should show validation errors
    await expect(page.getByText(/required|enter/i)).toBeVisible();
  });

  test('should redirect to dashboard after successful login', async ({ page }) => {
    // Fill in valid test credentials
    await page.getByLabel(/email/i).fill('test@example.com');
    await page.getByLabel(/password/i).fill('testpassword123');
    
    // Submit the form
    await page.getByRole('button', { name: /login|sign in/i }).click();
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
  });

  test('should have link to registration', async ({ page }) => {
    // Check for registration link
    const registerLink = page.getByRole('link', { name: /register|sign up|create account/i });
    await expect(registerLink).toBeVisible();
  });
});

test.describe('Protected Routes', () => {
  test('should redirect unauthenticated user to login', async ({ page }) => {
    // Try to access protected route without authentication
    await page.goto('/portfolio');
    
    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });

  test('should redirect unauthenticated user from trading', async ({ page }) => {
    await page.goto('/trading');
    await expect(page).toHaveURL(/login/);
  });

  test('should redirect unauthenticated user from analytics', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page).toHaveURL(/login/);
  });
});

test.describe('Logout Flow', () => {
  test.skip('should logout and redirect to login', async ({ page }) => {
    // This test requires being logged in first
    // Skip until auth flow is fully working
    
    // Assume logged in, find logout button
    await page.getByRole('button', { name: /logout|sign out/i }).click();
    
    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });
});
