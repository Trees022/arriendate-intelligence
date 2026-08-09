from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PropertySeed:
    id: UUID
    title: str
    description: str
    operation_type: str
    property_type: str
    city: str
    sector: str | None
    monthly_price: int | None
    sale_price: int | None
    bedrooms: int | None
    bathrooms: int | None
    parking_spaces: int | None
    pet_policy: str
    furnished: bool | None
    square_meters: float | None
    amenities: tuple[str, ...]
    availability_status: str = "available"

    def to_record(self) -> dict[str, object]:
        known_features = [
            self.title,
            self.description,
            f"Operación: {self.operation_type}",
            f"Tipo: {self.property_type}",
            f"Ciudad: {self.city}",
        ]
        if self.sector:
            known_features.append(f"Sector: {self.sector}")
        if self.bedrooms is not None:
            known_features.append(f"Dormitorios: {self.bedrooms}")
        if self.bathrooms is not None:
            known_features.append(f"Baños: {self.bathrooms}")
        if self.parking_spaces is not None:
            known_features.append(f"Estacionamientos: {self.parking_spaces}")
        known_features.append(f"Política de mascotas: {self.pet_policy}")
        if self.furnished is not None:
            known_features.append(f"Amoblado: {'sí' if self.furnished else 'no'}")
        if self.amenities:
            known_features.append(f"Comodidades: {', '.join(self.amenities)}")
        canonical_text = ". ".join(known_features)

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "operation_type": self.operation_type,
            "property_type": self.property_type,
            "city": self.city,
            "sector": self.sector,
            "monthly_price": self.monthly_price,
            "sale_price": self.sale_price,
            "currency": "CLP",
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "parking_spaces": self.parking_spaces,
            "pet_policy": self.pet_policy,
            "furnished": self.furnished,
            "square_meters": self.square_meters,
            "amenities": list(self.amenities),
            "availability_status": self.availability_status,
            "source_text": canonical_text,
            "embedding_text": canonical_text,
        }


DEMO_PROPERTIES: tuple[PropertySeed, ...] = (
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000001"),
        "Departamento Los Castaños",
        (
            "Departamento luminoso en un entorno residencial, con segundo dormitorio "
            "apto para escritorio."
        ),
        "rent",
        "apartment",
        "Viña del Mar",
        "Los Castaños",
        670_000,
        None,
        2,
        2,
        1,
        "allowed",
        False,
        68.0,
        ("balcón", "conserjería", "bodega"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000002"),
        "Estudio Poniente",
        "Estudio amoblado de distribución compacta y conexión rápida con el centro de Viña.",
        "rent",
        "studio",
        "Viña del Mar",
        "Poniente",
        480_000,
        None,
        1,
        1,
        0,
        "not_allowed",
        True,
        34.0,
        ("conserjería", "lavandería"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000003"),
        "Vista Jardín del Mar",
        (
            "Departamento amplio con terraza y espacios comunes, ubicado en un sector "
            "de carácter residencial."
        ),
        "rent",
        "apartment",
        "Viña del Mar",
        "Jardín del Mar",
        850_000,
        None,
        3,
        2,
        2,
        "unknown",
        False,
        92.0,
        ("terraza", "piscina", "bodega"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000004"),
        "Departamento Recreo Alto",
        (
            "Unidad de dos dormitorios en calle interior; la descripción del propietario "
            "destaca poco flujo vehicular."
        ),
        "rent",
        "apartment",
        "Viña del Mar",
        "Recreo",
        620_000,
        None,
        2,
        1,
        1,
        "allowed",
        False,
        61.0,
        ("balcón", "áreas verdes"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000005"),
        "Departamento Centro Viña",
        "Departamento renovado próximo al centro, con cocina equipada y locomoción cercana.",
        "rent",
        "apartment",
        "Viña del Mar",
        "Centro",
        590_000,
        None,
        2,
        1,
        None,
        "allowed",
        True,
        57.0,
        ("ascensor", "cocina equipada"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000006"),
        "Casa Familiar Miraflores",
        (
            "Casa independiente con patio, cuatro dormitorios y espacios diferenciados "
            "para trabajo o estudio."
        ),
        "buy",
        "house",
        "Viña del Mar",
        "Miraflores",
        None,
        285_000_000,
        4,
        3,
        2,
        "allowed",
        False,
        168.0,
        ("patio", "bodega", "quincho"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000007"),
        "Loft Cerro Alegre",
        "Loft amoblado en edificio restaurado, con espacio integrado y vista parcial a la bahía.",
        "rent",
        "loft",
        "Valparaíso",
        "Cerro Alegre",
        720_000,
        None,
        2,
        2,
        0,
        "allowed",
        True,
        76.0,
        ("terraza común", "bicicletero"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000008"),
        "Departamento Playa Ancha",
        "Departamento de tres dormitorios cercano a servicios universitarios y plazas del sector.",
        "rent",
        "apartment",
        "Valparaíso",
        "Playa Ancha",
        520_000,
        None,
        3,
        1,
        1,
        "allowed",
        False,
        72.0,
        ("bodega", "área de juegos"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000009"),
        "Departamento Barón Compacto",
        "Unidad de un dormitorio con acceso cercano a transporte público y comercio de barrio.",
        "rent",
        "apartment",
        "Valparaíso",
        "Barón",
        450_000,
        None,
        1,
        1,
        0,
        "not_allowed",
        False,
        42.0,
        ("conserjería", "gimnasio"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000010"),
        "Departamento Parque Curauma",
        (
            "Departamento familiar frente a áreas verdes, con tercer dormitorio "
            "utilizable como oficina."
        ),
        "rent",
        "apartment",
        "Valparaíso",
        "Curauma",
        680_000,
        None,
        3,
        2,
        1,
        "allowed",
        False,
        84.0,
        ("áreas verdes", "piscina", "bodega"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000011"),
        "Bosques de Montemar",
        (
            "Departamento de tres dormitorios con terraza amplia y distribución separada "
            "de áreas comunes."
        ),
        "rent",
        "apartment",
        "Concón",
        "Bosques de Montemar",
        980_000,
        None,
        3,
        2,
        2,
        "allowed",
        False,
        104.0,
        ("terraza", "piscina", "gimnasio", "bodega"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000012"),
        "Departamento Concón Centro",
        "Departamento funcional próximo a comercio local, con dos dormitorios y estacionamiento.",
        "rent",
        "apartment",
        "Concón",
        "Centro",
        610_000,
        None,
        2,
        2,
        1,
        "unknown",
        False,
        64.0,
        ("ascensor", "conserjería"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000013"),
        "Costa de Montemar Amoblado",
        "Departamento amoblado con balcón y espacio de comedor separado del estar.",
        "rent",
        "apartment",
        "Concón",
        "Costa de Montemar",
        780_000,
        None,
        2,
        2,
        1,
        "not_allowed",
        True,
        73.0,
        ("balcón", "piscina", "gimnasio"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000014"),
        "Casa Higuerillas",
        "Casa de dos niveles con patio protegido, cuatro dormitorios y sala independiente.",
        "buy",
        "house",
        "Concón",
        "Higuerillas",
        None,
        420_000_000,
        4,
        3,
        2,
        "allowed",
        False,
        190.0,
        ("patio", "sala multiuso", "bodega"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000015"),
        "Departamento El Belloto",
        "Departamento de dos dormitorios en condominio con áreas verdes y acceso controlado.",
        "rent",
        "apartment",
        "Quilpué",
        "El Belloto",
        470_000,
        None,
        2,
        1,
        1,
        "allowed",
        False,
        58.0,
        ("áreas verdes", "juegos infantiles"),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000016"),
        "Departamento Marga Marga",
        "Unidad de tres dormitorios con buena distribución interior y terraza cerrada.",
        "rent",
        "apartment",
        "Quilpué",
        "Marga Marga",
        560_000,
        None,
        3,
        2,
        1,
        "unknown",
        False,
        79.0,
        ("terraza", "conserjería"),
        "reserved",
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000017"),
        "Departamento Valencia",
        (
            "Registro sintético incompleto de una unidad económica; dormitorios y "
            "estacionamiento por confirmar."
        ),
        "rent",
        "apartment",
        "Quilpué",
        "Valencia",
        430_000,
        None,
        None,
        1,
        None,
        "allowed",
        None,
        None,
        (),
    ),
    PropertySeed(
        UUID("10000000-0000-4000-8000-000000000018"),
        "Casa Los Pinos",
        "Casa pareada con patio posterior, tres dormitorios y estacionamiento para dos vehículos.",
        "buy",
        "house",
        "Quilpué",
        "Los Pinos",
        None,
        135_000_000,
        3,
        2,
        2,
        "allowed",
        False,
        112.0,
        ("patio", "logia", "bodega"),
    ),
)
