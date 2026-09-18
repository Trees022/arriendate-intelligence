class IntegrationError(Exception):
    """Base error whose public message is safe to expose."""

    public_message = "La integración externa no pudo completar la operación."


class UnsupportedCapabilityError(IntegrationError):
    public_message = "El canal no soporta esta capacidad."


class IntegrationConfigurationError(IntegrationError):
    public_message = "La integración no está configurada."

