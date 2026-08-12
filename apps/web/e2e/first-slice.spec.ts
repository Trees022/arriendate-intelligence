import { expect, test } from "@playwright/test";

test("lead extraction, hard constraints, and grounded semantic matches", async ({ page }) => {
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
  await page.getByRole("button", { name: "Generar recomendaciones" }).click();
  await expect(page.locator(".matching-card")).toHaveCount(2);
  await expect(page.locator(".matching-summary")).toContainText("2 elegibles de 18");
  await expect(page.locator(".matching-card").first()).toContainText("restricciones verificadas");
  await expect(page.locator(".matching-card__price").first()).toContainText("670.000");
  const firstMatchTitle = await page.locator(".matching-card h3").first().textContent();
  await page.locator(".matching-card").first().getByRole("link", { name: /Ver propiedad/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(firstMatchTitle ?? "");
  await page.goBack();
  await expect(page.locator(".matching-card")).toHaveCount(2);
  await page.screenshot({ path: "../../.local/verified-lead-detail.png", fullPage: true });

  await page.reload();
  await expect(page.getByRole("heading", { name: "Requisitos estructurados" })).toBeVisible();
  await expect(page.locator(".matching-card")).toHaveCount(2);
  await page.getByText("Ejecuciones de IA").click();
  await expect(page.getByText("Validada", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Nuevo lead" }).click();
  await page.getByPlaceholder("Ej. Camila y Tomás").fill("Lead semántico E2E");
  await page.getByPlaceholder(/Somos una pareja joven/).fill(
    "Busco principalmente preferencias semánticas: algo tranquilo, luminoso y cerca del mar.",
  );
  await page.getByRole("button", { name: "Guardar lead" }).click();
  await page.getByRole("button", { name: "Extraer requisitos con IA" }).click();
  await page.getByRole("button", { name: "Generar recomendaciones" }).click();
  await expect(page.locator(".matching-summary")).toContainText("17 elegibles de 18");
  await expect(page.locator(".matching-card")).toHaveCount(3);
  await page.screenshot({ path: "../../.local/verified-semantic-matching.png", fullPage: true });

  await page.getByRole("link", { name: "Nuevo lead" }).click();
  await page.getByPlaceholder("Ej. Camila y Tomás").fill("Lead imposible E2E");
  await page.getByPlaceholder(/Somos una pareja joven/).fill(
    "Busco un departamento con presupuesto imposible de $100.000 en Viña del Mar.",
  );
  await page.getByRole("button", { name: "Guardar lead" }).click();
  await page.getByRole("button", { name: "Extraer requisitos con IA" }).click();
  await page.getByRole("button", { name: "Generar recomendaciones" }).click();
  await expect(page.getByText(/No hay propiedades que cumplan/)).toBeVisible();
  await expect(page.getByText(/presupuesto máximo: excluyó/)).toBeVisible();
  await expect(page.locator(".matching-card")).toHaveCount(0);
  await page.screenshot({ path: "../../.local/verified-zero-candidates.png", fullPage: true });
});
