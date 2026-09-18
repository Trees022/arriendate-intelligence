# Property Operations Pilot (M2)

## 1. Visión y Contexto Operacional

El piloto de operaciones inmobiliarias (`Property Operations Pilot`) evoluciona Arriendate Intelligence desde un prototipo de captura y matching hacia una plataforma operativa de publicación y distribución multicanal de propiedades.

### El problema del operador
Un operador o corredor inmobiliario recibe hoy múltiples propiedades semanalmente. De forma manual debe:
1. Recopilar datos técnicos y notas sueltas.
2. Organizar y seleccionar fotografías (portada, orden de visualización).
3. Redactar avisos adaptados al formato y tono de cada canal (Marketplace, Grupos de Facebook, portales como Yapo o PortalInmobiliario).
4. Publicar manualmente o mediante asistentes en cada destino.
5. Recordar qué canales ya tienen publicación activa y cuándo vence el período de enfriamiento (*cooldown*) para republicar sin ser penalizado o considerado spam.
6. Monitorear el estado comercial de la propiedad para pausar publicaciones si se reserva o arrienda.

### Tesis del producto
> **"Una propiedad se ingresa una sola vez."** A partir de ese momento, Arriendate asiste en preparar el paquete comercial, versionar según canal, orquestar campañas, controlar enfriamientos y mantener trazabilidad inmutable de publicaciones.

---

## 2. Modelo de Dominio y Estados

### 2.1 Extensiones a `Property`
Se amplía la entidad `Property` existente preservando compatibilidad con el motor de matching y los 18 seed records chilenos:
- `reference_code`: Código interno del operador (ej. `PRP-STGO-001`).
- `source_notes`: Notas de captación, llaves, visitas o antecedentes.
- `address_text`: Dirección o ubicación referencial visible.
- `built_area_m2`: Superficie construida en m².
- `land_area_m2`: Superficie total de terreno en m².
- `commercial_status`: Estado operacional de comercialización.
  - `draft`: Borrador inicial, en preparación.
  - `active`: Disponible para armar paquetes y lanzar campañas.
  - `reserved`: Con reserva en curso (pausa o previene nuevas campañas).
  - `closed`: Operación cerrada (arrendada/vendida).
  - `archived`: Retirada del catálogo operacional.

*Nota:* `availability_status` (`available`, `reserved`, `unavailable`) se conserva íntegro para compatibilidad con `matching_runs`.

### 2.2 Medios (`PropertyMedia`)
Almacenamiento y orden de fotografías de la propiedad:
- `id`: UUID.
- `property_id`: Referencia a la propiedad.
- `storage_key`: Identificador único de almacenamiento físico/local.
- `original_filename`: Nombre original del archivo subido.
- `media_type`: Tipo de medio (`image`).
- `mime_type`: MIME validado (`image/jpeg`, `image/png`, `image/webp`).
- `size_bytes`: Tamaño en bytes (límite 10MB por archivo).
- `position`: Entero para ordenamiento de galería.
- `is_cover`: Booleano determinando si es la foto principal/portada.

### 2.3 Paquetes de Publicación (`PublicationPackage`) y Variantes (`PublicationPackageVariant`)
- `PublicationPackage`: Representa una versión congelada del material de marketing derivado de la ficha y fotos de la propiedad.
  - `property_fingerprint`: Hash de la propiedad y sus medios al momento de generación para detectar desactualización (*staleness*).
  - `status`: `draft` -> `approved` -> `archived`.
- `PublicationPackageVariant`: Cada una de las adaptaciones de texto por canal:
  - `channel_type`: `facebook_marketplace`, `facebook_group`, `portal_inmobiliario`, `yapo`, `whatsapp_catalog`.
  - `headline`: Título optimizado para el canal.
  - `body`: Cuerpo del aviso formateado con saltos de línea y emojis apropiados.
  - `short_body`: Versión compacta para canales con límite de caracteres.
  - `highlights`: Array de viñetas clave (precio, dormitorios, estacionamiento, bodega).
  - `cta`: Llamado a la acción con canal de contacto.
  - `suggested_media_ids`: Lista ordenada de IDs de medios sugeridos para este canal.
  - `warnings`: Alertas operacionales (ej. "No incluir número de dpto en marketplace público").

### 2.4 Destinos de Publicación (`PublicationTarget`)
Canales o grupos configurados donde el operador distribuye:
- `name`: Nombre descriptivo (ej. *"Comunidad Departamentos Santiago Centro"*).
- `channel_type`: Tipo de canal.
- `execution_mode`:
  - `assisted`: Asistido con portapapeles y enlace directo al destino.
  - `manual`: Pasos manuales con checklist.
  - `api`: Conexión directa por API oficial (modelado para M3).
  - `local_agent`: Runner local automatizado (modelado para M3).
- `destination_url`: URL web o endpoint del grupo/portal.
- `minimum_repost_interval_hours`: Horas mínimas de espera antes de permitir una nueva publicación (ej. 72h para grupos de FB).
- `active`: Booleano para activar/desactivar el destino.

### 2.5 Campañas (`Campaign`) y Objetivos (`CampaignTarget`)
- Agrupa la distribución de un paquete aprobado hacia uno o más `PublicationTargets`.
- Estado: `draft` -> `active` -> `paused` -> `completed` -> `archived`.

### 2.6 Trabajos de Publicación (`PublicationJob`) y Publicaciones (`Publication`)
- `PublicationJob`: Unidad de ejecución de publicación para un target específico dentro de una campaña.
  - Estados:
    - `pending`: Creado, en espera.
    - `ready`: Listo para ejecutarse (enriquecido con contenido y medios).
    - `running`: En proceso de publicación asistida/manual.
    - `published`: Publicado exitosamente.
    - `failed`: Error en el proceso.
    - `cooldown`: Publicado previamente, esperando que transcurra `minimum_repost_interval_hours`.
    - `cancelled`: Cancelado por usuario o por cierre de propiedad.
- `Publication`: Registro histórico inmutable de una publicación realizada exitosamente:
  - Fecha exacta (`published_at`).
  - URL resultante de la publicación (`publication_url`).
  - Identificador de la versión del paquete y destino.

---

## 3. Mecanismo de Cooldown y Repost (Reconciliación)

1. Al marcar un job como `published`, se calcula `next_eligible_at = published_at + interval(target.minimum_repost_interval_hours)`.
2. El job pasa al estado `cooldown`.
3. El servicio de reconciliación (`repost_reconciler`), determinista e idempotente:
   - Recibe la hora actual (reloj inyectable `now: datetime`).
   - Busca jobs en `cooldown` donde `next_eligible_at <= now`.
   - Si la propiedad sigue en estado comercial `active` y la campaña está `active`, transiciona el job a `ready` para la siguiente publicación.
   - Si la propiedad no está activa, lo transiciona a `cancelled` o lo mantiene en pausa.

---

## 4. Estrategia de Almacenamiento y Generación

- **Almacenamiento Local First**: `PropertyMediaStorage` desacopla el sistema de archivos del código de negocio. Para P0, los archivos se guardan en un directorio local seguro (`apps/api/storage/media/`) con hashing y validación estricta de MIME.
- **Generador de Paquetes Fixture-First**: Generador determinístico sin dependencias externas ni costo de API para el flujo estándar de desarrollo y testing, con extensión opcional a `StructuredGenerator` de OpenAI/Anthropic si se configuran llaves.
