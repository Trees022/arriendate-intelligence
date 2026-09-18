import hashlib
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    PublicationPackageResponse,
    PublicationPackageVariantResponse,
)
from app.core.errors import NotFoundError
from app.db.models import Property, PropertyMedia, PublicationPackage, PublicationPackageVariant
from app.domain.enums import ChannelType, PackageStatus
from app.repositories.media import PropertyMediaRepository
from app.repositories.properties import PropertyRepository
from app.repositories.publication_packages import PublicationPackageRepository


def compute_property_fingerprint(
    prop: Property, media: list[PropertyMedia]
) -> str:
    media_tokens = [f"{m.id}:{m.position}:{m.is_cover}" for m in media]
    raw = (
        f"{prop.id}|{prop.title}|{prop.description}|{prop.operation_type}|"
        f"{prop.property_type}|{prop.city}|{prop.sector}|{prop.price}|{prop.currency}|"
        f"{prop.bedrooms}|{prop.bathrooms}|{prop.parking_spaces}|{prop.pet_policy}|"
        f"{prop.furnished}|{prop.square_meters}|{prop.reference_code}|"
        f"{prop.address_text}|{prop.built_area_m2}|{prop.land_area_m2}|"
        f"{','.join(sorted(prop.amenities))}|{';'.join(media_tokens)}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_channel_variants(
    prop: Property, media: list[PropertyMedia]
) -> list[dict[str, object]]:
    # Put cover first
    cover_media = [m.id for m in media if m.is_cover]
    other_media = [m.id for m in media if not m.is_cover]
    sorted_media_ids = cover_media + other_media

    price_str = f"${prop.price:,.0f} {prop.currency}".replace(",", ".")
    op_label = "Arriendo" if prop.operation_type == "rent" else "Venta"
    location = f"{prop.city}" + (f", {prop.sector}" if prop.sector else "")
    specs = []
    if prop.bedrooms:
        specs.append(f"{prop.bedrooms}D")
    if prop.bathrooms:
        specs.append(f"{prop.bathrooms}B")
    if prop.parking_spaces:
        specs.append(f"{prop.parking_spaces}E")
    if prop.square_meters:
        specs.append(f"{prop.square_meters}m²")
    specs_str = " | ".join(specs) if specs else "Características por confirmar"
    pet_label = {
        "allowed": "Permitidas",
        "not_allowed": "No permitidas",
        "unknown": "Por confirmar",
    }[prop.pet_policy]

    highlights = [
        f"Ubicación: {location}",
        f"Precio: {price_str}",
        f"Distribución: {specs_str}",
    ]
    if prop.pet_policy == "allowed":
        highlights.append("Mascotas: Aceptadas")
    elif prop.pet_policy == "not_allowed":
        highlights.append("Mascotas: No permitidas")
    if prop.furnished:
        highlights.append("Completamente amoblado")
    if prop.amenities:
        highlights.append(f"Comodidades: {', '.join(prop.amenities[:4])}")

    variants: list[dict[str, object]] = [
        {
            "channel_type": ChannelType.FACEBOOK_PAGE.value,
            "headline": f"{op_label}: {prop.title} en {location}",
            "body": (
                f"{prop.title}\n\n{prop.description}\n\n"
                f"Ubicación: {location}\nValor: {price_str}\n"
                f"Características: {specs_str}\n\n"
                "Escríbenos para recibir la ficha completa y coordinar una visita."
            ),
            "short_body": f"{prop.title} en {location}. {price_str}. {specs_str}.",
            "highlights": highlights,
            "cta": "Enviar mensaje para coordinar una visita.",
            "suggested_media_ids": sorted_media_ids[:10],
            "warnings": [],
        },
        {
            "channel_type": ChannelType.INSTAGRAM_PROFESSIONAL.value,
            "headline": f"{prop.title} · {location}",
            "body": (
                f"{prop.title}\n\n{prop.description}\n\n"
                f"{location} · {price_str} · {specs_str}\n\n"
                "Envíanos un DM para conocer disponibilidad y coordinar una visita."
            ),
            "short_body": f"{op_label} en {location} · {price_str}",
            "highlights": highlights,
            "cta": "Consultar por DM.",
            "suggested_media_ids": sorted_media_ids[:10],
            "warnings": ["Verificar el formato de las imágenes antes de publicar."],
        },
        # 1. Facebook Marketplace
        {
            "channel_type": ChannelType.FACEBOOK_MARKETPLACE.value,
            "headline": f"{prop.title} - {location} ({price_str})",
            "body": (
                f"✨ {prop.title} en {op_label} ✨\n\n"
                f"{prop.description}\n\n"
                f"📍 Ubicación: {location}\n"
                f"💰 Valor: {price_str}\n"
                f"📐 Características: {specs_str}\n\n"
                "ℹ️ Requisitos habituales de arriendo / compra aplican.\n"
                "📲 Para coordinar visitas o más información, contáctanos por mensaje directo."
            ),
            "short_body": (
                f"{op_label} en {location}: {prop.title}. {specs_str}. Valor: {price_str}."
            ),
            "highlights": highlights,
            "cta": "Envía un mensaje para más información y requisitos.",
            "suggested_media_ids": sorted_media_ids[:10],
            "warnings": ["No incluir dirección exacta ni número de depto en publicación pública."],
        },
        # 2. Facebook Group
        {
            "channel_type": ChannelType.FACEBOOK_GROUP.value,
            "headline": f"[{op_label}] {prop.title} en {location}",
            "body": (
                f"¡Hola comunidad! Les comparto esta excelente opción disponible en {location}:\n\n"
                f"🏡 {prop.title}\n\n"
                f"{prop.description}\n\n"
                f"• Precio: {price_str}\n"
                f"• {specs_str}\n"
                f"• Mascotas: {pet_label}\n\n"
                "Escríbeme o déjame un comentario para conocer disponibilidad y coordinar visita."
            ),
            "short_body": (
                f"Hola vecinos! Disponible en {location}: {prop.title} por {price_str}. "
                f"Consultas por interno."
            ),
            "highlights": highlights,
            "cta": "Escríbeme por mensaje directo para agendar visita.",
            "suggested_media_ids": sorted_media_ids[:6],
            "warnings": ["Respeta las normas del grupo respecto a precios visibles y contacto."],
        },
        # 3. Portal Inmobiliario
        {
            "channel_type": ChannelType.PORTAL_INMOBILIARIO.value,
            "headline": f"{prop.title}, {location}",
            "body": (
                f"Exclusiva oportunidad de {op_label.lower()} en {location}.\n\n"
                f"{prop.description}\n\n"
                "DETALLES DE LA PROPIEDAD:\n"
                + "\n".join(f"- {h}" for h in highlights)
                + "\n\nCoordine su visita con nuestro equipo de operaciones inmobiliarias."
            ),
            "short_body": f"{prop.title} en {location}. {price_str}. {specs_str}.",
            "highlights": highlights,
            "cta": "Solicitar orden de visita y dossier completo.",
            "suggested_media_ids": sorted_media_ids,
            "warnings": [],
        },
        # 4. Yapo
        {
            "channel_type": ChannelType.YAPO.value,
            "headline": f"{op_label} {prop.title} - {location}",
            "body": (
                f"{prop.title}\n"
                f"Sector: {location}\n"
                f"Precio: {price_str}\n\n"
                f"{prop.description}\n\n"
                f"Dormitorios/Baños: {specs_str}\n"
                "Trato serio y directo. Enviar mensaje para coordinar."
            ),
            "short_body": f"{op_label} en {location}. {price_str}. {specs_str}.",
            "highlights": highlights,
            "cta": "Contactar por formulario o teléfono.",
            "suggested_media_ids": sorted_media_ids[:8],
            "warnings": [],
        },
        # 5. WhatsApp Catalog
        {
            "channel_type": ChannelType.WHATSAPP_CATALOG.value,
            "headline": f"*{prop.title}* ({location})",
            "body": (
                f"*{prop.title}*\n"
                f"📍 *Sector:* {location}\n"
                f"💵 *Precio:* {price_str}\n"
                f"📐 *Ficha:* {specs_str}\n\n"
                f"{prop.description}\n\n"
                f"✅ *Detalles:*\n"
                + "\n".join(f"• {h}" for h in highlights)
                + "\n\n_Escríbeme para solicitar más información o coordinar una visita._"
            ),
            "short_body": f"*{prop.title}* - {location} | {price_str} | {specs_str}",
            "highlights": highlights,
            "cta": "Reenviar ficha o coordinar visita.",
            "suggested_media_ids": sorted_media_ids[:5],
            "warnings": [],
        },
        {
            "channel_type": ChannelType.GENERIC.value,
            "headline": f"{prop.title} - {location}",
            "body": (
                f"{prop.title}\n\n{prop.description}\n\n"
                f"Ubicación: {location}\nValor: {price_str}\n{specs_str}"
            ),
            "short_body": f"{prop.title} · {location} · {price_str}",
            "highlights": highlights,
            "cta": "Solicitar más información.",
            "suggested_media_ids": sorted_media_ids,
            "warnings": [],
        },
    ]
    return variants


class PublicationPackageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = PublicationPackageRepository(session)
        self.property_repository = PropertyRepository(session)
        self.media_repository = PropertyMediaRepository(session)

    async def generate_package(self, property_id: UUID) -> PublicationPackageResponse:
        prop = await self.property_repository.get(property_id)
        if not prop:
            raise NotFoundError("Propiedad no encontrada")

        media = await self.media_repository.list_by_property(property_id)
        fingerprint = compute_property_fingerprint(prop, media)

        package = await self.repository.create_package(
            property_id=property_id,
            property_fingerprint=fingerprint,
            status=PackageStatus.DRAFT.value,
        )

        variants_data = generate_channel_variants(prop, media)
        for v in variants_data:
            v["package_id"] = package.id

        variants = await self.repository.create_variants(variants_data)
        return self._to_response(package, variants)

    async def get_package(self, package_id: UUID) -> PublicationPackageResponse:
        package = await self.repository.get(package_id)
        if not package:
            raise NotFoundError("Paquete de publicación no encontrado")
        variants = await self.repository.list_variants(package_id)
        return self._to_response(package, variants)

    async def list_by_property(
        self, property_id: UUID
    ) -> list[PublicationPackageResponse]:
        packages = await self.repository.list_by_property(property_id)
        result: list[PublicationPackageResponse] = []
        for pkg in packages:
            variants = await self.repository.list_variants(pkg.id)
            result.append(self._to_response(pkg, variants))
        return result

    async def approve_package(self, package_id: UUID) -> PublicationPackageResponse:
        package = await self.repository.get(package_id)
        if not package:
            raise NotFoundError("Paquete de publicación no encontrado")
        approved = await self.repository.approve_package(package)
        variants = await self.repository.list_variants(package_id)
        return self._to_response(approved, variants)

    async def is_stale(self, package_id: UUID) -> bool:
        package = await self.repository.get(package_id)
        if not package:
            raise NotFoundError("Paquete no encontrado")
        prop = await self.property_repository.get(package.property_id)
        if not prop:
            return True
        media = await self.media_repository.list_by_property(prop.id)
        current_fingerprint = compute_property_fingerprint(prop, media)
        return current_fingerprint != package.property_fingerprint

    def _to_response(
        self,
        package: PublicationPackage,
        variants: list[PublicationPackageVariant],
    ) -> PublicationPackageResponse:
        variant_responses = [
            PublicationPackageVariantResponse(
                id=v.id,
                package_id=v.package_id,
                channel_type=ChannelType(v.channel_type),
                headline=v.headline,
                body=v.body,
                short_body=v.short_body,
                highlights=list(v.highlights),
                cta=v.cta,
                suggested_media_ids=list(v.suggested_media_ids),
                warnings=list(v.warnings),
                created_at=v.created_at,
            )
            for v in variants
        ]
        return PublicationPackageResponse(
            id=package.id,
            property_id=package.property_id,
            property_fingerprint=package.property_fingerprint,
            status=PackageStatus(package.status),
            variants=variant_responses,
            created_at=package.created_at,
            updated_at=package.updated_at,
        )
