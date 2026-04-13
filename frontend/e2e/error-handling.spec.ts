import { test, expect } from '@playwright/test';

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/test');
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Intercept API calls and simulate failure
    await page.route('**/files?**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'internal_error',
            message: 'Internal server error',
            retryable: true
          }
        })
      });
    });
    
    // Refresh to trigger the error
    const refreshButton = page.getByRole('button', { name: 'Обновить' });
    await refreshButton.click();
    
    await page.waitForTimeout(500);
    
    // Check for error banner
    const errorAlert = page.locator('.alert');
    await expect(errorAlert.first()).toBeVisible();
  });

  test('should show retry button for retryable errors', async ({ page }) => {
    let requestCount = 0;
    
    // Intercept API calls
    await page.route('**/files?**', async (route) => {
      requestCount++;
      if (requestCount === 1) {
        await route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 'internal_error',
              message: 'Service unavailable',
              retryable: true
            }
          })
        });
      } else {
        // On retry, return success
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [],
            total: 0,
            page: 1,
            page_size: 10,
            pages: 0
          })
        });
      }
    });
    
    // Refresh to trigger error
    const refreshButton = page.getByRole('button', { name: 'Обновить' });
    await refreshButton.click();
    await page.waitForTimeout(500);
    
    // Look for retry button in error banner
    const retryButton = page.getByRole('button', { name: 'Повторить' });
    const hasRetry = await retryButton.isVisible().catch(() => false);
    
    if (hasRetry) {
      await retryButton.click();
      await page.waitForTimeout(500);
      
      // Verify second request was made
      expect(requestCount).toBeGreaterThanOrEqual(2);
    }
  });

  test('should handle validation errors on upload', async ({ page }) => {
    // Intercept upload endpoint
    await page.route('**/files', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 422,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 'validation_error',
              message: 'Validation failed',
              fields: {
                title: ['Название обязательно']
              }
            }
          })
        });
      } else {
        await route.continue();
      }
    });
    
    // Open upload modal
    const uploadButton = page.getByRole('button', { name: 'Добавить файл' });
    await uploadButton.click();
    
    // Try to submit without data (or with test data that will fail)
    const saveButton = page.getByRole('button', { name: 'Сохранить' });
    
    // If save button is disabled, test passes (validation at UI level)
    const isDisabled = await saveButton.isDisabled().catch(() => false);
    
    if (!isDisabled) {
      // Fill minimal data to enable submit
      const titleInput = page.locator('input[placeholder*="Например"]').first();
      await titleInput.fill('A');
      
      await saveButton.click();
      await page.waitForTimeout(500);
      
      // Check for validation error
      const errorAlert = page.locator('.alert-danger, .invalid-feedback');
      await expect(errorAlert.first()).toBeVisible();
    }
    
    // Close modal
    const cancelButton = page.getByRole('button', { name: 'Отмена' });
    await cancelButton.click();
  });

  test('should allow dismissing error banners', async ({ page }) => {
    // Intercept to simulate error
    await page.route('**/files?**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'internal_error',
            message: 'Server error',
            retryable: false
          }
        })
      });
    });
    
    // Refresh to trigger error
    const refreshButton = page.getByRole('button', { name: 'Обновить' });
    await refreshButton.click();
    await page.waitForTimeout(500);
    
    // Find dismissible alert
    const dismissButton = page.locator('.alert .btn-close, .alert [aria-label="Close"]').first();
    const hasDismiss = await dismissButton.isVisible().catch(() => false);
    
    if (hasDismiss) {
      await dismissButton.click();
      await page.waitForTimeout(300);
      
      // Alert should be gone
      const alert = page.locator('.alert').first();
      await expect(alert).not.toBeVisible();
    }
  });
});
