# Property Command Center (M3)

## Tesis de producto

Arriendate registra una propiedad una vez y organiza su ciclo comercial desde esa propiedad. El objeto central no es una cuenta social ni una publicación de Facebook:

```text
Property
  -> contenido comercial versionado
  -> distribución
  -> publicaciones
  -> engagement
  -> conversaciones
  -> leads (cuando exista atribución explícita)
  -> seguimiento y resultados
```

El Command Center responde dos preguntas: qué está ocurriendo comercialmente con la propiedad y qué debería ocurrir después.

## Arquitectura actual

`GET /api/properties/{id}/command-center` agrega en el servidor:

- propiedad y estado comercial;
- cuentas de canal y capacidades;
- targets, último job, última publicación y cooldown;
- variante aprobada y orden de fotos preparado;
- último snapshot de engagement por publicación;
- comentarios recientes;
- conversaciones y mensajes atribuidos;
- campañas e historial;
- próximas acciones determinísticas.

React recibe una vista tipada. No calcula cooldowns, atribución, staleness ni prioridades.

## Property como aggregate root

Las relaciones preservan la procedencia:

```text
Publication -> Property + Campaign + Target + PublicationPackage
EngagementSnapshot -> Publication -> Property
PublicationComment -> Publication -> Property
Conversation -> Publication? -> Property?
Conversation -> Lead?
```

Los vínculos de conversación son nulos cuando no existe evidencia. Un comentario o mensaje no crea un lead automáticamente.

## Meta oficial y Meta asistido

Las superficies se modelan por separado.

| Superficie | Modo actual | Límite honesto |
|---|---|---|
| Facebook Page | adapter oficial/fixture | La demo no llama a Meta; una conexión real requiere OAuth, permisos y App Review. |
| Messenger de Page | adapter de conversación separado | No representa acceso al inbox personal de Facebook. |
| Instagram Professional | adapter oficial/fixture | Las capacidades reales dependen de cuenta, permisos y aprobación. |
| Facebook Groups | `assisted` | No se implementa publicación Graph API para grupos arbitrarios. |
| Facebook Marketplace | `assisted` | No se afirma una API pública general para publicar inmuebles. |

No existe un `MetaDoesEverythingService`. Los contratos pequeños son `SocialPublishingProvider`, `EngagementProvider` y `ConversationProvider`; los adapters fixture de Page, Messenger e Instagram viven separados bajo `integrations/meta`.

## Modelo de capacidades

Cada cuenta o destino expone, por capacidad, uno de estos estados:

- `available`;
- `unavailable`;
- `requires_permission`;
- `requires_connection`;
- `assisted_only`.

Las capacidades tipadas son `publish_content`, `read_comments`, `reply_comments`, `read_messages`, `send_messages`, `read_reactions`, `read_metrics`, `schedule_content`, `automatic_repost` y `assisted_publish`.

La validación de dominio y PostgreSQL impide crear un target de Facebook Group o Marketplace con `execution_mode=api`.

## Modos de ejecución

- `api`: una API oficial soportada podría ejecutar la acción desde servidor.
- `assisted`: Arriendate prepara todo y el operador ejecuta la acción externa.
- `manual`: Arriendate registra una actividad realizada fuera del sistema.
- `local_agent`: frontera futura para un runner autorizado por el usuario; no está implementado.

La demo sólo simula capacidades oficiales. No publica ni sincroniza datos reales.

## Flujo asistido

Para Groups y Marketplace, cada job ofrece:

- abrir el destino guardado;
- copiar titular, cuerpo y hechos verificados;
- revisar advertencias y CTA;
- ver fotos y orden preparado;
- pegar la URL publicada;
- marcar como completo e iniciar cooldown;
- marcar que requiere acción;
- registrar una falla mediante API.

El operador no vuelve a buscar la propiedad, el precio, el texto, las fotos, el target ni la fecha de repost.

## Conversation domain

`conversations` guarda cuenta, ID externo con scope por cuenta, canal, estado y atribuciones opcionales a propiedad, publicación y lead. `messages` usa un ID externo único dentro de la conversación y distingue `inbound`/`outbound`.

Estados: `open`, `needs_reply`, `handled`, `archived`.

La ingesta de fixtures/proveedores es idempotente por `(conversation_id, external_message_id)`.

## Engagement domain

`engagement_snapshots` mantiene historia por publicación. Los contadores de comentarios, reacciones, vistas, impresiones y mensajes son nulos cuando la plataforma no los expone. `null` significa “No disponible”; `0` significa que se midió cero.

`publication_comments` guarda el comentario necesario para operar respuestas, no el payload crudo completo del proveedor. La ingesta es idempotente por `(publication_id, external_comment_id)`.

## Motor de próximas acciones

Las acciones se calculan desde el estado actual y no se persisten. No usan IA. Actualmente detectan:

- paquete aprobado obsoleto después de cambiar hechos o fotos;
- propiedad sin fotos;
- target listo para publicación inicial;
- target listo para repost después del cooldown;
- job fallido o marcado como `action_required`;
- conversación que necesita respuesta;
- comentario pendiente;
- campaña pausada.

La prioridad es determinística (`high`, `medium`, `low`).

## Demo sin credenciales

Con `ARRIENDATE_SEED_DEMO_DATA=true`, el seed idempotente crea para la primera propiedad sintética:

- una Facebook Page fixture;
- una cuenta Instagram Professional fixture;
- dos Facebook Groups asistidos;
- un target Marketplace asistido;
- publicaciones históricas, un cooldown y un repost listo;
- métricas disponibles y no disponibles;
- comentarios;
- una conversación Messenger `needs_reply` con mensajes.

Todos estos registros tienen `is_demo=true`, usan URLs `example.invalid` y la interfaz los identifica como fixtures.

## Seguridad

- No se persisten tokens OAuth ni credenciales Meta.
- Los errores de integración tienen mensajes públicos sanitizados.
- El frontend no muta Supabase directamente.
- Las nuevas tablas habilitan RLS y revocan privilegios de `anon` y `authenticated`.
- Los textos y IDs externos están acotados.
- No hay bypass de CAPTCHA, verificación, rate limits ni protecciones anti-automatización.
- La aplicación sigue siendo single-operator e interna; autenticación y tenancy son requisitos previos a SaaS público.

## Frontera del runner local futuro

```text
Arriendate Server
  -> PublicationJob explícitamente autorizado
  -> Arriendate Runner en el entorno del operador
  -> navegador controlado por el operador
  -> plataforma asistida
```

El runner no guardará credenciales personales en la nube, deberá detenerse ante CAPTCHA o verificación, respetará restricciones de plataforma y devolverá evidencia de éxito/falla. M3 sólo conserva `local_agent` en el modelo; no implementa automatización de navegador.

## Flujo piloto

1. Crear o completar una propiedad con hechos reales.
2. Subir y ordenar fotos; elegir portada.
3. Generar, revisar y aprobar el `PublicationPackage`.
4. Elegir targets reutilizables y crear campaña.
5. Operar los jobs asistidos desde `/properties/{id}/command-center`.
6. Registrar URL/fecha y dejar que el cooldown produzca la próxima acción.
7. Revisar engagement y conversaciones atribuidas sin convertirlas automáticamente en leads.

## Limitaciones actuales

- No hay OAuth, webhooks ni sincronización en vivo con Meta.
- Page, Messenger e Instagram usan adapters fixture.
- No hay respuesta a comentarios o mensajes desde la UI.
- Las acciones no se notifican fuera de la aplicación.
- No hay analítica de lead calificado, visita o cierre todavía.
- No hay autenticación, multi-tenancy ni backend PostgreSQL con rol de mínimo privilegio.

## Próximo hito recomendado

Validar el flujo asistido con 5–20 propiedades reales del piloto, corregir fricción de carga/edición de propiedades y fotos, y recién después implementar la conexión OAuth de una Facebook Page e Instagram Professional en sandbox. Para la conexión real faltan: aplicación Meta, URLs HTTPS y políticas públicas, OAuth state/PKCE, almacenamiento cifrado y rotación de tokens, permisos aprobados, webhooks verificados, scopes por cuenta, backfill idempotente y observabilidad de rate limits.

