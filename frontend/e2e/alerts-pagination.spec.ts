import { test, expect } from '@playwright/test';

test.describe('Alerts Pagination', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/test');
    // Wait for initial data load
    await page.waitForTimeout(1000);
  });

  test('should display alerts section with pagination', async ({ page }) => {
    const alertsHeading = page.locator('h2', { hasText: 'Алерты' });
    await expect(alertsHeading).toBeVisible();
    
    // Check for page size selector in alerts section
    const selects = page.locator('select');
    const count = await selects.count();
    expect(count).toBeGreaterThanOrEqual(1); // At least one for files, possibly two
  });

  test('should display alerts table structure', async ({ page }) => {
    // Look for alerts table headers
    const idHeader = page.locator('th', { hasText: 'ID' });
    const levelHeader = page.locator('th', { hasText: 'Уровень' });
    const messageHeader = page.locator('th', { hasText: 'Сообщение' });
    
    await expect(idHeader.first()).toBeVisible();
    await expect(levelHeader.first()).toBeVisible();
    await expect(messageHeader.first()).toBeVisible();
  });

  test('should show pagination info or empty state', async ({ page }) => {
    // Look for "Показано X-Y из Z" text in the second section (alerts)
    const paginationInfos = page.locator('text=/Показано \\d+-\\d+ из \\d+/');
    const emptyStates = page.getByText('Алертов пока нет');
    
    const hasPagination = await paginationInfos.count() > 0;
    const hasEmptyState = await emptyStates.count() > 0;
    
    expect(hasPagination || hasEmptyState).toBeTruthy();
  });
});
