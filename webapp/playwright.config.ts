import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  retries: 1,
  use: {
    baseURL: "http://127.0.0.1:10895",
    headless: true,
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command:
        "uv run uvicorn dreame_mcp.server:app --host 127.0.0.1 --port 10894 --log-level warning",
      port: 10894,
      cwd: "../",
      timeout: 30000,
      reuseExistingServer: false,
    },
    {
      command: "npm run dev",
      port: 10895,
      timeout: 30000,
      reuseExistingServer: false,
    },
  ],
});
