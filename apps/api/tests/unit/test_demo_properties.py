from app.data.properties import DEMO_PROPERTIES


def test_demo_inventory_has_required_size_and_variation() -> None:
    assert len(DEMO_PROPERTIES) >= 15
    assert {property_record.city for property_record in DEMO_PROPERTIES} == {
        "Viña del Mar",
        "Valparaíso",
        "Concón",
        "Quilpué",
    }
    assert {property_record.operation_type for property_record in DEMO_PROPERTIES} == {
        "rent",
        "buy",
    }
    assert {property_record.pet_policy for property_record in DEMO_PROPERTIES} == {
        "allowed",
        "not_allowed",
        "unknown",
    }
    assert any(property_record.parking_spaces is None for property_record in DEMO_PROPERTIES)
    assert any(property_record.furnished is None for property_record in DEMO_PROPERTIES)
    assert len({property_record.id for property_record in DEMO_PROPERTIES}) == len(DEMO_PROPERTIES)


def test_embedding_source_omits_unknown_features() -> None:
    incomplete = next(item for item in DEMO_PROPERTIES if item.title == "Departamento Valencia")
    record = incomplete.to_record()

    assert "Dormitorios:" not in str(record["embedding_text"])
    assert "Estacionamientos:" not in str(record["embedding_text"])
    assert "Amoblado:" not in str(record["embedding_text"])
