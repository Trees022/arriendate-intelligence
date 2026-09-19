import { expect, test } from "@playwright/test";

test("property-first broker workflow from dashboard to command center", async ({ page }) => {
  test.setTimeout(60_000);

  await page.goto("/dashboard");
  const mainNav = page.getByRole("navigation", { name: "Navegación principal" });
  await expect(page.getByRole("heading", { name: /Tu cartera, publicaciones/ })).toBeVisible();
  await expect(page.getByRole("main").getByRole("link", { name: "+ Nueva propiedad" })).toBeVisible();
  await page.screenshot({ path: "../../.local/product-dashboard.png", fullPage: true });

  await mainNav.getByRole("link", { name: "Propiedades", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Propiedades", exact: true })).toBeVisible();
  await page.screenshot({ path: "../../.local/product-properties.png", fullPage: true });

  await page.getByRole("main").getByRole("link", { name: "+ Nueva propiedad" }).click();
  await expect(page.getByRole("heading", { name: /Prepara una propiedad/ })).toBeVisible();
  await expect(page.getByRole("list", { name: "Progreso del registro" }).getByRole("listitem")).toHaveCount(4);
  await page.screenshot({ path: "../../.local/product-new-property-wizard.png", fullPage: true });

  const propertyTitle = `Casa piloto UX ${Date.now()}`;
  await page.getByPlaceholder("Ej. Departamento en Castro centro").fill(propertyTitle);
  await page.getByRole("textbox", { name: "Precio" }).fill("$ 720.000");
  await page.getByLabel("Comuna o ciudad").fill("Castro");
  await page.getByRole("button", { name: "Guardar y seguir" }).click();

  await expect(page.getByRole("heading", { name: "Fotos" })).toBeVisible();
  await page.getByLabel(/Agregar fotos/).setInputFiles({
    name: "fachada-piloto.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAANSURBVBhXY6hd3v8fAAYLArMu9ToqAAAAAElFTkSuQmCC",
      "base64",
    ),
  });
  await page.getByRole("button", { name: "Seguir a publicación" }).click();
  await page.getByRole("button", { name: "Generar publicación" }).click();
  await expect(page.getByText("Vista previa")).toBeVisible();
  await page.getByRole("button", { name: "Aprobar y seguir" }).click();

  const groupTarget = page.getByRole("checkbox", { name: /Propiedades Región de Los Lagos/ });
  await expect(groupTarget).toBeVisible();
  await groupTarget.check();
  await page.getByRole("button", { name: "Iniciar campaña" }).click();

  await expect(page).toHaveURL(/\/properties\/[0-9a-f-]+\/command-center$/);
  await expect(page.getByRole("heading", { name: propertyTitle })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Actualizar paquete de publicación" })).toHaveCount(0);
  await page.screenshot({ path: "../../.local/product-command-center.png", fullPage: true });

  await mainNav.getByRole("link", { name: "Publicaciones", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Publicaciones", exact: true })).toBeVisible();
  const publicationRow = page.locator(".publication-queue__item").filter({ hasText: propertyTitle });
  await publicationRow.locator("summary").click();
  await expect(publicationRow.getByText("Kit de publicación preparado")).toBeVisible();
  await page.screenshot({ path: "../../.local/product-publications.png", fullPage: true });

  await mainNav.getByRole("link", { name: "Inbox", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Inbox", exact: true })).toBeVisible();
  await page.screenshot({ path: "../../.local/product-inbox.png", fullPage: true });

  await mainNav.getByRole("link", { name: "Leads", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Leads", exact: true })).toBeVisible();
});
