import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: ["demo.spec.ts", "demo-v2.spec.ts"],
  fullyParallel: false,
  retries: 0,
  workers: 1,
  timeout: 300_000, // 5 minutes max for full demo

  use: {
    baseURL: process.env.DEMO_BASE_URL || "http://localhost:8000",
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
