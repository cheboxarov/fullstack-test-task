import { test, expect } from '@playwright/test';

/**
 * End-to-end user workflow tests
 * Tests complete user journeys from start to finish
 */
test.describe('User Workflows', () => {
  test('complete workflow: load page, view data, refresh, handle errors', async ({ page }) => {
    // Step 1: Navigate to dashboard
    await page.goto('/test');
    
    // Verify page loads successfully
    await expect(page.getByRole('heading', { name: 'Управление файлами' })).toBeVisible();
    
    // Step 2: Wait for initial data load
    await page.waitForTimeout(1000);
    
    // Verify sections are present
    await expect(page.getByRole('heading', { name: 'Файлы' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Алерты' })).toBeVisible();
    
    // Step 3: Check pagination state (either data exists or empty state)
    const hasFilesData = await page.locator('table tbody tr').first().isVisible().catch(() => false);
    const filesEmptyState = await page.getByText('Файлы пока не загружены').isVisible().catch(() => false);
    
    expect(hasFilesData || filesEmptyState).toBeTruthy();
    
    // Step 4: Click refresh
    const refreshButton = page.getByRole('button', { name: 'Обновить' });
    await refreshButton.click();
    
    // Wait for refresh to complete
    await page.waitForTimeout(1000);
    
    // Verify page still functional after refresh
    await expect(page.getByRole('heading', { name: 'Управление файлами' })).toBeVisible();
    
    // Step 5: Open and close upload modal
    const uploadButton = page.getByRole('button', { name: 'Добавить файл' });
    await uploadButton.click();
    
    // Verify modal opened
    await expect(page.getByText('Добавить файл', { exact: false }).first()).toBeVisible();
    
    // Close modal
    const cancelButton = page.getByRole('button', { name: 'Отмена' });
    await cancelButton.click();
    
    // Verify modal closed
    await expect(page.getByText('Добавить файл', { exact: false }).first()).not.toBeVisible();
    
    // Step 6: Verify page state is consistent
    await expect(page.getByRole('button', { name: 'Обновить' })).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Добавить файл' })).toBeEnabled();
  });

  test('pagination workflow: change page size and navigate', async ({ page }) => {
    await page.goto('/test');
    await page.waitForTimeout(1000);
    
    // Get all page size selectors (files and alerts)
    const pageSizeSelectors = page.locator('select');
    const count = await pageSizeSelectors.count();
    
    if (count === 0) {
      test.skip();
      return;
    }
    
    // Change first page size selector (files)
    const firstSelector = pageSizeSelectors.first();
    await firstSelector.selectOption('25');
    
    await page.waitForTimeout(500);
    
    // Verify value changed
    await expect(firstSelector).toHaveValue('25');
    
    // Try to navigate pages if pagination exists
    const pagination = page.locator('.pagination').first();
    const hasPagination = await pagination.isVisible().catch(() => false);
    
    if (hasPagination) {
      // Get current page
      const activePage = pagination.locator('.page-item.active');
      const initialPage = await activePage.textContent();
      
      // Try to go to next page
      const nextButton = pagination.locator('.page-item').filter({ hasText: '›' }).first();
      const isDisabled = await nextButton.evaluate(el => el.classList.contains('disabled'));
      
      if (!isDisabled) {
        await nextButton.click();
        await page.waitForTimeout(500);
        
        // Verify page changed
        const newActivePage = pagination.locator('.page-item.active');
        const newPageText = await newActivePage.textContent();
        expect(newPageText).not.toBe(initialPage);
      }
    }
  });

  test('resilient workflow: handles API failures gracefully', async ({ page }) => {
    await page.goto('/test');
    await page.waitForTimeout(500);
    
    // Simulate API failure for files
    await page.route('**/files?**', async (route) => {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'service_unavailable',
            message: 'Service temporarily unavailable',
            retryable: true
          }
        })
      });
    });
    
    // Click refresh to trigger error
    await page.getByRole('button', { name: 'Обновить' }).click();
    await page.waitForTimeout(500);
    
    // Verify error is shown
    const alert = page.locator('.alert').first();
    await expect(alert).toBeVisible();
    
    // Verify UI is still functional (buttons not disabled)
    await expect(page.getByRole('button', { name: 'Обновить' })).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Добавить файл' })).toBeEnabled();
    
    // User can still open upload modal
    await page.getByRole('button', { name: 'Добавить файл' }).click();
    await expect(page.getByText('Добавить файл', { exact: false }).first()).toBeVisible();
  });
});
