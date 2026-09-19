from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import PropertyCreate, PropertyUpdate
from app.core.errors import NotFoundError, ValidationError
from app.db.models import Property
from app.domain.enums import AvailabilityStatus, CommercialStatus, OperationType
from app.repositories.properties import PropertyRepository


def build_property_canonical_text(
    *,
    title: str,
    description: str,
    operation_type: str,
    property_type: str,
    city: str,
    sector: str | None,
    bedrooms: int | None,
    bathrooms: int | None,
    parking_spaces: int | None,
    pet_policy: str,
    furnished: bool | None,
    amenities: list[str],
) -> str:
    known_features = [value for value in (title, description) if value]
    known_features.extend(
        [
            f"Operación: {operation_type}",
            f"Tipo: {property_type}",
            f"Ciudad: {city}",
        ]
    )
    if sector:
        known_features.append(f"Sector: {sector}")
    if bedrooms is not None:
        known_features.append(f"Dormitorios: {bedrooms}")
    if bathrooms is not None:
        known_features.append(f"Baños: {bathrooms}")
    if parking_spaces is not None:
        known_features.append(f"Estacionamientos: {parking_spaces}")
    known_features.append(f"Política de mascotas: {pet_policy}")
    if furnished is not None:
        known_features.append(f"Amoblado: {'sí' if furnished else 'no'}")
    if amenities:
        known_features.append(f"Comodidades: {', '.join(amenities)}")
    return ". ".join(known_features)


class PropertyService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = PropertyRepository(session)

    async def get(self, property_id: UUID) -> Property:
        property_record = await self.repository.get(property_id)
        if not property_record:
            raise NotFoundError("Propiedad no encontrada")
        return property_record

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        operation_type: OperationType | None,
        city: str | None,
        availability: AvailabilityStatus | None,
        commercial_status: CommercialStatus | None = None,
    ) -> tuple[list[Property], int]:
        return await self.repository.list(
            page=page,
            page_size=page_size,
            operation_type=operation_type,
            city=city,
            availability=availability,
            commercial_status=commercial_status,
        )

    async def create(self, payload: PropertyCreate) -> Property:
        description = payload.description.strip() or payload.title
        canonical_text = build_property_canonical_text(
            title=payload.title,
            description=description,
            operation_type=payload.operation_type.value,
            property_type=payload.property_type,
            city=payload.city,
            sector=payload.sector,
            bedrooms=payload.bedrooms,
            bathrooms=payload.bathrooms,
            parking_spaces=payload.parking_spaces,
            pet_policy=payload.pet_policy.value,
            furnished=payload.furnished,
            amenities=payload.amenities,
        )
        record: dict[str, object] = {
            "title": payload.title,
            "description": description,
            "operation_type": payload.operation_type.value,
            "property_type": payload.property_type,
            "city": payload.city,
            "sector": payload.sector,
            "monthly_price": payload.monthly_price,
            "sale_price": payload.sale_price,
            "currency": payload.currency,
            "bedrooms": payload.bedrooms,
            "bathrooms": payload.bathrooms,
            "parking_spaces": payload.parking_spaces,
            "pet_policy": payload.pet_policy.value,
            "furnished": payload.furnished,
            "square_meters": payload.square_meters,
            "reference_code": payload.reference_code,
            "source_notes": payload.source_notes,
            "address_text": payload.address_text,
            "built_area_m2": (
                Decimal(str(payload.built_area_m2)) if payload.built_area_m2 is not None else None
            ),
            "land_area_m2": (
                Decimal(str(payload.land_area_m2)) if payload.land_area_m2 is not None else None
            ),
            "commercial_status": payload.commercial_status.value,
            "amenities": payload.amenities,
            "availability_status": AvailabilityStatus.AVAILABLE.value,
            "source_text": canonical_text,
            "embedding_text": canonical_text,
        }
        return await self.repository.create(record)

    async def update(self, property_id: UUID, payload: PropertyUpdate) -> Property:
        prop = await self.get(property_id)
        data = payload.model_dump(exclude_unset=True)

        if "description" in data and not data["description"].strip():
            data["description"] = data.get("title", prop.title)

        # Convert Enum fields to values
        if "operation_type" in data and data["operation_type"] is not None:
            data["operation_type"] = data["operation_type"].value
        if "pet_policy" in data and data["pet_policy"] is not None:
            data["pet_policy"] = data["pet_policy"].value
        if "commercial_status" in data and data["commercial_status"] is not None:
            data["commercial_status"] = data["commercial_status"].value
        if "availability_status" in data and data["availability_status"] is not None:
            data["availability_status"] = data["availability_status"].value
        if "built_area_m2" in data and data["built_area_m2"] is not None:
            data["built_area_m2"] = Decimal(str(data["built_area_m2"]))
        if "land_area_m2" in data and data["land_area_m2"] is not None:
            data["land_area_m2"] = Decimal(str(data["land_area_m2"]))

        next_operation = data.get("operation_type", prop.operation_type)
        next_monthly_price = data.get("monthly_price", prop.monthly_price)
        next_sale_price = data.get("sale_price", prop.sale_price)
        if next_operation == OperationType.RENT.value and (
            next_monthly_price is None or next_sale_price is not None
        ):
            raise ValidationError(
                "Para arriendo, debe especificar monthly_price y no sale_price"
            )
        if next_operation == OperationType.BUY.value and (
            next_sale_price is None or next_monthly_price is not None
        ):
            raise ValidationError(
                "Para compra, debe especificar sale_price y no monthly_price"
            )

        # Rebuild canonical text if core fields changed
        title = data.get("title", prop.title)
        description = data.get("description", prop.description)
        operation_type = data.get("operation_type", prop.operation_type)
        property_type = data.get("property_type", prop.property_type)
        city = data.get("city", prop.city)
        sector = data.get("sector", prop.sector)
        bedrooms = data.get("bedrooms", prop.bedrooms)
        bathrooms = data.get("bathrooms", prop.bathrooms)
        parking_spaces = data.get("parking_spaces", prop.parking_spaces)
        pet_policy = data.get("pet_policy", prop.pet_policy)
        furnished = data.get("furnished", prop.furnished)
        amenities = data.get("amenities", prop.amenities)

        new_canonical = build_property_canonical_text(
            title=title,
            description=description,
            operation_type=operation_type,
            property_type=property_type,
            city=city,
            sector=sector,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            parking_spaces=parking_spaces,
            pet_policy=pet_policy,
            furnished=furnished,
            amenities=amenities,
        )
        data["source_text"] = new_canonical
        data["embedding_text"] = new_canonical

        return await self.repository.update(prop, data)
