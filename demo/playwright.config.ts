import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "demo.spec.ts",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  timeout: 180_000, // 3 minutes max for full demo

  use: {
    baseURL: "http://localhost:5173",
    video: "on",
    viewport: { width: 1440, height: 900 },
    launchOptions: {
      slowMo: 60, // Slow enough for video legibility
    },
  },

  projects: [
    {
      name: "demo",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
