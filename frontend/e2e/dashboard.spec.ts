import { test, expect } from '@playwright/test';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/test');
  });

  test('should display page title and header', async ({ page }) => {
    await expect(page).toHaveTitle(/Тестовое задание/);
    
    const heading = page.getByRole('heading', { name: 'Управление файлами' });
    await expect(heading).toBeVisible();
    
    const description = page.getByText('Загрузка файлов, просмотр статусов обработки и ленты алертов');
    await expect(description).toBeVisible();
  });

  test('should display files section', async ({ page }) => {
    const filesHeading = page.getByRole('heading', { name: 'Файлы' });
    await expect(filesHeading).toBeVisible();
    
    // Check table headers
    await expect(page.getByText('Название')).toBeVisible();
    await expect(page.getByText('Файл')).toBeVisible();
    await expect(page.getByText('MIME')).toBeVisible();
    await expect(page.getByText('Размер')).toBeVisible();
    await expect(page.getByText('Статус')).toBeVisible();
  });

  test('should display alerts section', async ({ page }) => {
    const alertsHeading = page.getByRole('heading', { name: 'Алерты' });
    await expect(alertsHeading).toBeVisible();
    
    // Check table headers
    await expect(page.getByText('ID')).toBeVisible();
    await expect(page.getByText('File ID')).toBeVisible();
    await expect(page.getByText('Уровень')).toBeVisible();
  });

  test('should have refresh and upload buttons', async ({ page }) => {
    const refreshButton = page.getByRole('button', { name: 'Обновить' });
    await expect(refreshButton).toBeVisible();
    await expect(refreshButton).toBeEnabled();
    
    const uploadButton = page.getByRole('button', { name: 'Добавить файл' });
    await expect(uploadButton).toBeVisible();
    await expect(uploadButton).toBeEnabled();
  });

  test('should show pagination controls when data exists', async ({ page }) => {
    // Wait for data to load
    await page.waitForTimeout(1000);
    
    // Check for pagination or empty state
    const paginationOrEmpty = await page.locator('.pagination, .text-secondary:has-text("Файлы пока не загружены")').first();
    await expect(paginationOrEmpty).toBeVisible();
  });
});
