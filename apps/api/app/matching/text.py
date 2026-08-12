from app.db.models import LeadRequirement, Property


def build_property_embedding_text(property_record: Property) -> str:
    facts = [
        property_record.title,
        property_record.description,
        f"Operación: {property_record.operation_type}",
        f"Tipo: {property_record.property_type}",
        f"Ciudad: {property_record.city}",
    ]
    if property_record.sector:
        facts.append(f"Sector: {property_record.sector}")
    if property_record.bedrooms is not None:
        facts.append(f"Dormitorios: {property_record.bedrooms}")
    if property_record.bathrooms is not None:
        facts.append(f"Baños: {property_record.bathrooms}")
    if property_record.parking_spaces is not None:
        facts.append(f"Estacionamientos: {property_record.parking_spaces}")
    facts.append(f"Política de mascotas: {property_record.pet_policy}")
    if property_record.furnished is not None:
        facts.append(f"Amoblado: {'sí' if property_record.furnished else 'no'}")
    if property_record.amenities:
        facts.append(f"Comodidades: {', '.join(property_record.amenities)}")
    return ". ".join(facts)


def build_lead_semantic_text(requirements: LeadRequirement) -> str | None:
    preferences = [f"Preferencia: {value}" for value in requirements.soft_preferences]
    if requirements.furnished_preference is not None:
        preference = "amoblado" if requirements.furnished_preference else "sin amoblar"
        preferences.append(f"Preferencia de amoblado: {preference}")
    return ". ".join(preferences) or None
