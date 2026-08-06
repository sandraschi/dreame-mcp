import { expect, test } from "@playwright/test";

const BE = "http://127.0.0.1:10894";

test.describe("Fleet Audit", () => {
  test("Backend health returns 200", async ({ request }) => {
    const resp = await request.get(`${BE}/api/v1/health`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe("ok");
    expect(body.service).toBe("dreame-mcp");
  });

  test("Backend diagnostics lists tools", async ({ request }) => {
    const resp = await request.get(`${BE}/api/v1/diagnostics`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.tool_count).toBeGreaterThanOrEqual(4);
    const names = body.tools.map((t: { name: string }) => t.name);
    expect(names).toContain("dreame_tool");
  });

  test("Backend skills endpoint", async ({ request }) => {
    const resp = await request.get(`${BE}/api/skills`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.skills.length).toBeGreaterThanOrEqual(1);
  });

  test("Frontend SPA loads without console errors", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    await page.goto("/", { timeout: 15000 });
    await page.waitForTimeout(3000);
    await expect(page.locator("#root")).toBeAttached();
    expect(page.locator('[data-testid="dashboard"]')).toHaveCount(1);
    expect(consoleErrors).toEqual([]);
  });

  test("Sidebar navigation reaches all pages without 404s", async ({
    page,
  }) => {
    const failed: string[] = [];
    page.on("response", (resp) => {
      if (resp.status() >= 400 && !resp.url().includes("/api/")) {
        failed.push(`${resp.status()} ${resp.url()}`);
      }
    });
    await page.goto("/", { timeout: 15000 });
    await page.waitForTimeout(2000);
    const routes = [
      ["LIDAR Map", "LIDAR Map"],
      ["Status", "Status"],
      ["Controls", "Controls"],
      ["MCP Tools", "MCP Tools"],
      ["Logs", "Logs"],
      ["Settings", "Settings"],
      ["Help", "Help"],
    ];
    for (const [label, heading] of routes) {
      await page
        .getByRole("navigation")
        .getByRole("link", { name: label })
        .click();
      await page.waitForTimeout(800);
      await expect(
        page.getByRole("heading", { name: heading }).first(),
      ).toBeVisible();
    }
    expect(failed).toEqual([]);
  });
});
