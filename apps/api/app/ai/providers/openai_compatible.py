import asyncio
from typing import Any, Literal, cast

import httpx

from app.ai.contracts import (
    StructuredGenerationRequest,
    StructuredGenerationResult,
)
from app.ai.errors import ProviderError


class OpenAICompatibleStructuredGenerator:
    """Responses API adapter using strict JSON Schema structured output."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        reasoning_effort: Literal["none", "low", "medium", "high"] = "low",
        timeout_seconds: float = 45,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.25,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key
        self._model = model
        self.reasoning_effort = reasoning_effort
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.transport = transport

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    @property
    def model(self) -> str:
        return self._model

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResult:
        payload = self._build_payload(request)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await self._post_with_bounded_retries(client, payload)

        try:
            body = cast(dict[str, Any], response.json())
        except ValueError as error:
            raise ProviderError(
                code="invalid_provider_response",
                message="El proveedor devolvió una respuesta no JSON",
            ) from error

        status = body.get("status")
        if status in {"failed", "incomplete", "cancelled"}:
            raise ProviderError(
                code=f"provider_{status}",
                message="El proveedor no completó la extracción",
            )

        output_text = self._extract_output_text(body)
        usage_value = body.get("usage")
        usage: dict[str, Any] = usage_value if isinstance(usage_value, dict) else {}
        provider_request_id = self._optional_string(body.get("id")) or response.headers.get(
            "x-request-id"
        )
        return StructuredGenerationResult(
            output_text=output_text,
            provider=self.provider_name,
            model=self._optional_string(body.get("model")) or self.model,
            provider_request_id=provider_request_id,
            input_tokens=self._optional_int(usage.get("input_tokens")),
            output_tokens=self._optional_int(usage.get("output_tokens")),
        )

    def _build_payload(self, request: StructuredGenerationRequest) -> dict[str, Any]:
        return {
            "model": self.model,
            "input": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "reasoning": {"effort": self.reasoning_effort},
            "text": {
                "verbosity": "low",
                "format": {
                    "type": "json_schema",
                    "name": request.schema_name,
                    "description": "Validated real-estate lead requirements",
                    "schema": request.schema,
                    "strict": True,
                },
            },
            "max_output_tokens": 1_500,
            "store": False,
        }

    async def _post_with_bounded_retries(
        self, client: httpx.AsyncClient, payload: dict[str, Any]
    ) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.post("responses", json=payload)
            except httpx.TimeoutException as error:
                if attempt < self.max_retries:
                    await self._backoff(attempt)
                    continue
                raise ProviderError(
                    code="provider_timeout",
                    message="El proveedor de IA excedió el tiempo de espera",
                    retryable=True,
                ) from error
            except httpx.RequestError as error:
                if attempt < self.max_retries:
                    await self._backoff(attempt)
                    continue
                raise ProviderError(
                    code="provider_unavailable",
                    message="No fue posible conectar con el proveedor de IA",
                    retryable=True,
                ) from error

            retryable_status = (
                response.status_code in {408, 409, 429} or response.status_code >= 500
            )
            if retryable_status and attempt < self.max_retries:
                await self._backoff(attempt)
                continue
            if response.is_error:
                raise ProviderError(
                    code=f"provider_http_{response.status_code}",
                    message="El proveedor de IA rechazó la solicitud",
                    retryable=retryable_status,
                )
            return response

        raise AssertionError("bounded retry loop exited unexpectedly")

    async def _backoff(self, attempt: int) -> None:
        await asyncio.sleep(self.retry_delay_seconds * (2**attempt))

    @staticmethod
    def _extract_output_text(body: dict[str, Any]) -> str:
        direct_text = body.get("output_text")
        if isinstance(direct_text, str) and direct_text:
            return direct_text

        output = body.get("output")
        if not isinstance(output, list):
            output = []
        text_parts: list[str] = []
        refused = False
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content_items = item.get("content")
            if not isinstance(content_items, list):
                continue
            for content in content_items:
                if not isinstance(content, dict):
                    continue
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    text_parts.append(content["text"])
                if content.get("type") == "refusal":
                    refused = True
        if text_parts:
            return "".join(text_parts)
        if refused:
            raise ProviderError(
                code="provider_refusal",
                message="El proveedor rechazó procesar esta solicitud",
            )
        raise ProviderError(
            code="missing_provider_output",
            message="El proveedor no devolvió contenido estructurado",
        )

    @staticmethod
    def _optional_string(value: object) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None
