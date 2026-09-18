import { expect, test } from "@playwright/test";

test("property-first broker workflow from dashboard to command center", async ({ page }) => {
  test.setTimeout(60_000);

  await page.goto("/dashboard");
  const mainNav = page.getByRole("navigation", { name: "Navegación principal" });
  await expect(page.getByRole("heading", { name: /Tu cartera, publicaciones/ })).toBeVisible();
  await expect(page.getByRole("main").getByRole("link", { name: "+ Nueva propiedad" })).toBeVisible();
  await expect(page.getByText("Propiedades activas")).toBeVisible();
  await page.screenshot({ path: "../../.local/product-dashboard.png", fullPage: true });

  await mainNav.getByRole("link", { name: "Propiedades", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Propiedades", exact: true })).toBeVisible();
  await expect(page.getByText("Abrir centro de operación").first()).toBeVisible();
  await page.screenshot({ path: "../../.local/product-properties.png", fullPage: true });

  await page.getByRole("main").getByRole("link", { name: "+ Nueva propiedad" }).click();
  await expect(page.getByRole("heading", { name: /Prepara una propiedad/ })).toBeVisible();
  await page.screenshot({ path: "../../.local/product-new-property-wizard.png", fullPage: true });

  const propertyTitle = `Casa piloto UX ${Date.now()}`;
  await page.getByPlaceholder("Ej. Casa luminosa en Castro centro").fill(propertyTitle);
  await page.getByPlaceholder("Describe sólo características verificables de la propiedad.").fill(
    "Casa luminosa de tres dormitorios con patio y estacionamiento.",
  );
  await page.getByPlaceholder("650000").fill("720000");
  await page.getByRole("textbox", { name: "Ciudad" }).fill("Castro");
  await page.getByRole("button", { name: "Guardar y continuar" }).click();

  await expect(page.getByRole("heading", { name: "Fotografías" })).toBeVisible();
  await page.getByLabel(/Seleccionar fotografías/).setInputFiles({
    name: "fachada-piloto.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAANSURBVBhXY6hd3v8fAAYLArMu9ToqAAAAAElFTkSuQmCC",
      "base64",
    ),
  });
  await expect(page.getByText("fachada-piloto.png")).toBeVisible();
  await page.getByRole("button", { name: "Continuar con contenido" }).click();
  await page.getByRole("button", { name: "Generar contenido" }).click();
  await expect(page.getByText("Vista previa")).toBeVisible();
  await page.getByRole("button", { name: "Aprobar contenido y continuar" }).click();

  const groupTarget = page.getByRole("checkbox", { name: /Propiedades Región de Los Lagos/ });
  await expect(groupTarget).toBeVisible();
  await groupTarget.check();
  await page.getByRole("button", { name: "Revisar lanzamiento" }).click();
  await expect(page.getByRole("heading", { name: "Todo listo para lanzar" })).toBeVisible();
  await page.getByRole("button", { name: "Activar propiedad y lanzar campaña" }).click();

  await expect(page).toHaveURL(/\/properties\/[0-9a-f-]+\/command-center$/);
  await expect(page.getByRole("heading", { name: propertyTitle })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dónde está publicada y qué sigue" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Actualizar paquete de publicación" })).toHaveCount(0);
  await page.screenshot({ path: "../../.local/product-command-center.png", fullPage: true });

  await mainNav.getByRole("link", { name: "Publicaciones", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Publicaciones", exact: true })).toBeVisible();
  const publicationRow = page.locator(".publication-queue__item").filter({ hasText: propertyTitle });
  await expect(publicationRow).toBeVisible();
  await publicationRow.locator("summary").click();
  await expect(publicationRow.getByText("Kit de publicación preparado")).toBeVisible();
  await page.screenshot({ path: "../../.local/product-publications.png", fullPage: true });

  await mainNav.getByRole("link", { name: "Inbox", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Inbox", exact: true })).toBeVisible();
  await expect(page.getByText(/todavía no existe sincronización en vivo con Meta/)).toBeVisible();
  await page.screenshot({ path: "../../.local/product-inbox.png", fullPage: true });

  await mainNav.getByRole("link", { name: "Leads", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Leads", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "+ Registrar lead" })).toBeVisible();
});
