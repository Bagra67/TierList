import { defineConfig, devices } from '@playwright/test';

import { E2E_APP_URL } from './e2e/support/app.ts';

const isCi: boolean = process.env.CI === 'true';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: isCi,
  retries: isCi ? 2 : 0,
  reporter: isCi ? [['github'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL: E2E_APP_URL,
    locale: 'fr-FR',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
  webServer: {
    command: 'node e2e/start-app.ts',
    url: `${E2E_APP_URL}/api/health`,
    reuseExistingServer: !isCi,
    timeout: 120_000,
    stdout: 'pipe',
  },
});
