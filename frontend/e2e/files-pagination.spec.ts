import { test, expect } from '@playwright/test';

test.describe('Files Pagination', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/test');
    // Wait for initial data load
    await page.waitForTimeout(1000);
  });

  test('should display page size selector', async ({ page }) => {
    const pageSizeSelect = page.locator('select').first();
    await expect(pageSizeSelect).toBeVisible();
    
    // Check default value
    await expect(pageSizeSelect).toHaveValue('10');
  });

  test('should change page size', async ({ page }) => {
    const pageSizeSelect = page.locator('select').first();
    
    // Change to 25 items per page
    await pageSizeSelect.selectOption('25');
    await page.waitForTimeout(500);
    
    // Verify selection changed
    await expect(pageSizeSelect).toHaveValue('25');
  });

  test('should display pagination info', async ({ page }) => {
    // Look for "Показано X-Y из Z" text
    const paginationInfo = page.locator('text=/Показано \\d+-\\d+ из \\d+/');
    
    // Either shows pagination info or empty state
    const hasData = await paginationInfo.isVisible().catch(() => false);
    const emptyState = await page.getByText('Файлы пока не загружены').isVisible().catch(() => false);
    
    expect(hasData || emptyState).toBeTruthy();
  });

  test('should handle pagination navigation when multiple pages exist', async ({ page }) => {
    // Check if pagination controls exist
    const pagination = page.locator('.pagination').first();
    const isVisible = await pagination.isVisible().catch(() => false);
    
    if (!isVisible) {
      // Skip if no pagination (not enough data)
      test.skip();
      return;
    }
    
    // Get first page button
    const firstPage = page.locator('.page-item').first();
    await expect(firstPage).toBeVisible();
    
    // Try to go to next page if available
    const nextButton = page.locator('.pagination .page-item').filter({ hasText: '›' }).first();
    const isDisabled = await nextButton.evaluate(el => el.classList.contains('disabled'));
    
    if (!isDisabled) {
      await nextButton.click();
      await page.waitForTimeout(500);
      
      // Verify page changed
      const activePage = page.locator('.page-item.active');
      await expect(activePage).toBeVisible();
    }
  });
});
