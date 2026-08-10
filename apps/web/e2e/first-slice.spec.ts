import { expect, test } from "@playwright/test";

test("inventory, durable lead intake, and observable structured extraction", async ({ page }) => {
  const originalRequest =
    "Somos una pareja joven con un perro. Buscamos departamento en Viña del Mar, máximo $700.000 mensuales, idealmente 2 dormitorios y estacionamiento.";

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: /Buenas decisiones empiezan/ })).toBeVisible();

  await page.getByRole("link", { name: "Propiedades" }).click();
  await expect(page.locator(".filter-bar__count strong")).toHaveText("18");
  await page.screenshot({ path: "../../.local/verified-inventory.png", fullPage: true });
  await page.getByRole("link", { name: /Departamento Los Castaños/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Departamento Los Castaños" })).toBeVisible();
  await expect(page.getByText("Admite mascotas")).toBeVisible();

  await page.getByRole("link", { name: "Nuevo lead" }).click();
  await page.getByPlaceholder("Ej. Camila y Tomás").fill("Lead E2E sintético");
  await page.getByPlaceholder(/Somos una pareja joven/).fill(originalRequest);
  await page.screenshot({ path: "../../.local/verified-intake.png", fullPage: true });
  await page.getByRole("button", { name: "Guardar lead" }).click();

  await expect(page).toHaveURL(/\/leads\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { level: 1, name: "Lead E2E sintético" })).toBeVisible();
  await expect(page.locator("blockquote")).toHaveText(originalRequest);

  await page.reload();
  await expect(page.locator("blockquote")).toHaveText(originalRequest);
  await page.getByRole("button", { name: "Extraer requisitos con IA" }).click();
  await expect(page.getByRole("heading", { name: "Requisitos estructurados" })).toBeVisible();
  await expect(page.getByText("CLP 700.000")).toBeVisible();
  await expect(
    page.locator(".requirements-grid > div").filter({ hasText: "Dormitorios mínimos" }).getByText("2"),
  ).toBeVisible();
  await expect(page.getByText("Calificado")).toBeVisible();
  await page.getByText("Ejecuciones de IA").click();
  await expect(page.getByText("Validada", { exact: true })).toBeVisible();
  await expect(page.getByText("fixture-structured-v1")).toBeVisible();
  await page.screenshot({ path: "../../.local/verified-lead-detail.png", fullPage: true });

  await page.reload();
  await expect(page.getByRole("heading", { name: "Requisitos estructurados" })).toBeVisible();
  await page.getByText("Ejecuciones de IA").click();
  await expect(page.getByText("Validada", { exact: true })).toBeVisible();
});
