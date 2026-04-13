import { test as base } from '@playwright/test';

/**
 * Global test fixtures and utilities
 */
export const test = base.extend({
  // Add custom fixtures here if needed
});

export { expect } from '@playwright/test';
