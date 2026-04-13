# E2E Tests

This directory contains Playwright E2E tests for the frontend application.

## Structure

```
e2e/
├── fixtures.ts              # Shared test fixtures
├── fixtures/                # Test data files
│   └── test-document.txt
├── dashboard.spec.ts        # Dashboard page tests
├── files-pagination.spec.ts # Files pagination tests
├── alerts-pagination.spec.ts # Alerts pagination tests
├── file-upload.spec.ts      # File upload flow tests
└── error-handling.spec.ts   # Error handling tests
```

## Running Tests

```bash
# Run all E2E tests headless
npm run test:e2e

# Run with UI mode (interactive)
npm run test:e2e:ui

# Run in debug mode
npm run test:e2e:debug

# Show HTML report
npm run test:e2e:report

# Run specific test file
npx playwright test dashboard.spec.ts

# Run with specific project
npx playwright test --project=chromium
```

## Test Categories

### Dashboard Tests (`dashboard.spec.ts`)
- Page load and header display
- Files section visibility
- Alerts section visibility
- Button states (Refresh, Upload)
- Initial data loading

### Files Pagination Tests (`files-pagination.spec.ts`)
- Page size selector functionality
- Pagination info display
- Page navigation (next/prev)
- Edge cases with empty data

### Alerts Pagination Tests (`alerts-pagination.spec.ts`)
- Alerts table structure
- Pagination controls
- Empty state handling

### File Upload Tests (`file-upload.spec.ts`)
- Modal open/close
- Form validation
- State reset on close
- Upload flow (with mocked backend)

### Error Handling Tests (`error-handling.spec.ts`)
- Network error display
- Retry functionality
- Validation errors
- Error dismissal

## Configuration

Tests are configured in `playwright.config.ts`:
- Base URL: `http://localhost:3000`
- Default browser: Chromium (Desktop Chrome)
- Viewport: 1280x720
- Auto-start dev server before tests
- HTML report generation

## Writing New Tests

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/test');
  });

  test('should do something', async ({ page }) => {
    // Test code here
  });
});
```

## Best Practices

1. **Use role-based selectors** when possible:
   ```typescript
   page.getByRole('button', { name: 'Submit' })
   ```

2. **Wait for network idle** after actions:
   ```typescript
   await page.waitForLoadState('networkidle');
   ```

3. **Mock API calls** for consistent test data:
   ```typescript
   await page.route('**/api/**', async (route) => {
     await route.fulfill({ json: mockData });
   });
   ```

4. **Use test ids** for elements without semantic roles:
   ```typescript
   page.locator('[data-testid="file-list"]')
   ```
