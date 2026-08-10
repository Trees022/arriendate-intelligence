from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.contracts import StructuredGenerator
from app.ai.costs import estimate_token_cost
from app.ai.errors import ProviderError
from app.ai.prompts import PROMPT_VERSION, build_lead_extraction_request
from app.ai.schemas import LeadRequirements
from app.core.errors import (
    AIProviderResponseError,
    AIProviderUnavailableError,
    InvalidAIOutputError,
    NotFoundError,
)
from app.core.settings import Settings
from app.db.models import AIRun, Lead, LeadRequirement
from app.domain.enums import LeadStatus
from app.repositories.extractions import ExtractionRepository
from app.repositories.leads import LeadRepository


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    lead: Lead
    requirements: LeadRequirement
    run: AIRun


class LeadExtractionService:
    def __init__(
        self,
        session: AsyncSession,
        generator: StructuredGenerator,
        settings: Settings,
    ) -> None:
        self.session = session
        self.generator = generator
        self.settings = settings
        self.leads = LeadRepository(session)
        self.extractions = ExtractionRepository(session)

    async def extract(self, lead_id: UUID) -> ExtractionResult:
        lead = await self.leads.get(lead_id)
        if lead is None:
            raise NotFoundError("Lead no encontrado")

        run = await self.extractions.create_run(
            lead_id=lead_id,
            provider=self.generator.provider_name,
            model=self.generator.model,
            prompt_version=PROMPT_VERSION,
        )
        started = perf_counter()
        request = build_lead_extraction_request(lead.original_request)

        try:
            provider_result = await self.generator.generate_structured(request)
        except ProviderError as error:
            latency_ms = self._elapsed_ms(started)
            await self.extractions.mark_run_failed(
                run_id=run.id,
                latency_ms=latency_ms,
                error_code=error.code,
                error_message=error.safe_message,
            )
            if error.code != "provider_not_configured" and not error.retryable:
                raise AIProviderResponseError(error.safe_message) from error
            raise AIProviderUnavailableError(
                error.safe_message, timeout=error.code == "provider_timeout"
            ) from error

        try:
            requirements = LeadRequirements.model_validate_json(provider_result.output_text)
        except ValidationError as error:
            latency_ms = self._elapsed_ms(started)
            await self.extractions.mark_run_failed(
                run_id=run.id,
                latency_ms=latency_ms,
                error_code="invalid_model_output",
                error_message="La salida del proveedor no cumplió el esquema validado",
            )
            raise InvalidAIOutputError from error

        try:
            requirement_record = await self.extractions.upsert_requirements(
                lead_id=lead_id,
                requirements=requirements,
                model=provider_result.model,
                prompt_version=PROMPT_VERSION,
            )
            lead.status = (
                LeadStatus.NEEDS_INFORMATION.value
                if requirements.missing_information
                else LeadStatus.QUALIFIED.value
            )
            estimated_cost = estimate_token_cost(
                input_tokens=provider_result.input_tokens,
                output_tokens=provider_result.output_tokens,
                input_cost_per_million=self.settings.ai_input_cost_per_million,
                output_cost_per_million=self.settings.ai_output_cost_per_million,
            )
            completed_run = await self.extractions.mark_run_succeeded(
                run_id=run.id,
                provider=provider_result.provider,
                model=provider_result.model,
                provider_request_id=provider_result.provider_request_id,
                latency_ms=self._elapsed_ms(started),
                input_tokens=provider_result.input_tokens,
                output_tokens=provider_result.output_tokens,
                estimated_cost=estimated_cost,
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self.extractions.mark_run_failed(
                run_id=run.id,
                latency_ms=self._elapsed_ms(started),
                error_code="persistence_error",
                error_message="No fue posible persistir la extracción validada",
            )
            raise

        return ExtractionResult(
            lead=lead,
            requirements=requirement_record,
            run=completed_run,
        )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, round((perf_counter() - started) * 1000))
