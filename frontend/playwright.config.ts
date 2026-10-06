import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './browser-tests',
  use: {baseURL: 'http://127.0.0.1:3000', launchOptions: {
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined,
  }},
  webServer: {command: 'npm run dev -- --hostname 127.0.0.1', url: 'http://127.0.0.1:3000', reuseExistingServer: false},
});
