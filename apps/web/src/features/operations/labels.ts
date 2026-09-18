import type { PropertyCommandCenter } from "../../lib/types";

export const channelLabels: Record<string, string> = {
  facebook_page: "Facebook",
  instagram_professional: "Instagram",
  facebook_group: "Grupo de Facebook",
  facebook_marketplace: "Marketplace",
  portal_inmobiliario: "Portal Inmobiliario",
  yapo: "Yapo",
  whatsapp_catalog: "WhatsApp",
  website: "Sitio web",
  email: "Correo",
  messenger: "Messenger",
  generic: "Otro canal",
};

export const distributionStatusLabels: Record<string, string> = {
  ready: "Listo para publicar",
  ready_to_repost: "Listo para republicar",
  cooldown: "En espera",
  requires_action: "Requiere acción",
  failed: "Falló",
  published: "Publicado",
  not_scheduled: "Sin campaña",
};

export const commercialStatusLabels: Record<string, string> = {
  draft: "Borrador",
  active: "Activa",
  reserved: "Reservada",
  closed: "Cerrada",
  archived: "Archivada",
};

export const campaignStatusLabels: Record<string, string> = {
  draft: "Borrador",
  active: "Activa",
  paused: "Pausada",
  completed: "Completada",
  archived: "Archivada",
};

export function commandCenterCover(center: PropertyCommandCenter) {
  const media = center.distribution.flatMap((item) => item.prepared_media);
  return media.find((item) => item.is_cover) ?? media[0] ?? null;
}

export function formatOperationsDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("es-CL", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
