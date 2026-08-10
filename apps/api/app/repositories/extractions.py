from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import LeadRequirements
from app.db.models import AIRun, LeadRequirement


class ExtractionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(
        self,
        *,
        lead_id: UUID,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> AIRun:
        run = AIRun(
            run_type="lead_extraction",
            lead_id=lead_id,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            status="running",
            validation_passed=False,
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_requirements(self, lead_id: UUID) -> LeadRequirement | None:
        return await self.session.scalar(
            select(LeadRequirement).where(LeadRequirement.lead_id == lead_id)
        )

    async def list_runs(self, lead_id: UUID, *, limit: int = 10) -> list[AIRun]:
        rows = await self.session.scalars(
            select(AIRun)
            .where(AIRun.lead_id == lead_id, AIRun.run_type == "lead_extraction")
            .order_by(AIRun.created_at.desc(), AIRun.id.desc())
            .limit(limit)
        )
        return list(rows)

    async def upsert_requirements(
        self,
        *,
        lead_id: UUID,
        requirements: LeadRequirements,
        model: str,
        prompt_version: str,
    ) -> LeadRequirement:
        values = requirements.model_dump(mode="json")
        confidence = values.pop("confidence")
        bind = self.session.get_bind()
        if bind.dialect.name == "postgresql":
            insert_values = {
                "id": uuid4(),
                "lead_id": lead_id,
                "extraction_confidence": confidence,
                "extraction_model": model,
                "prompt_version": prompt_version,
                **values,
            }
            update_values = {
                "extraction_confidence": confidence,
                "extraction_model": model,
                "prompt_version": prompt_version,
                "updated_at": func.now(),
                **values,
            }
            statement = (
                postgresql_insert(LeadRequirement)
                .values(**insert_values)
                .on_conflict_do_update(
                    constraint="lead_requirements_lead_id_key",
                    set_=update_values,
                )
                .returning(LeadRequirement.id)
            )
            record_id = (await self.session.execute(statement)).scalar_one()
            record = await self.session.get(LeadRequirement, record_id)
            if record is None:
                raise RuntimeError("Lead requirements disappeared during upsert")
            return record

        record = await self.get_requirements(lead_id)
        if record is None:
            record = LeadRequirement(
                lead_id=lead_id,
                extraction_confidence=confidence,
                extraction_model=model,
                prompt_version=prompt_version,
                **values,
            )
            self.session.add(record)
        else:
            for field, value in values.items():
                setattr(record, field, value)
            record.extraction_confidence = confidence
            record.extraction_model = model
            record.prompt_version = prompt_version
        await self.session.flush()
        return record

    async def mark_run_succeeded(
        self,
        *,
        run_id: UUID,
        provider: str,
        model: str,
        provider_request_id: str | None,
        latency_ms: int,
        input_tokens: int | None,
        output_tokens: int | None,
        estimated_cost: Decimal | None,
    ) -> AIRun:
        run = await self._required_run(run_id)
        run.provider = provider
        run.model = model
        run.provider_request_id = provider_request_id
        run.latency_ms = latency_ms
        run.input_tokens = input_tokens
        run.output_tokens = output_tokens
        run.estimated_cost = estimated_cost
        run.validation_passed = True
        run.status = "succeeded"
        run.error_code = None
        run.error_message = None
        await self.session.flush()
        return run

    async def mark_run_failed(
        self,
        *,
        run_id: UUID,
        latency_ms: int,
        error_code: str,
        error_message: str,
    ) -> AIRun:
        run = await self._required_run(run_id)
        run.latency_ms = latency_ms
        run.validation_passed = False
        run.status = "failed"
        run.error_code = error_code[:80]
        run.error_message = error_message[:300]
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def _required_run(self, run_id: UUID) -> AIRun:
        run = await self.session.get(AIRun, run_id)
        if run is None:
            raise RuntimeError("AI run disappeared during extraction")
        return run
