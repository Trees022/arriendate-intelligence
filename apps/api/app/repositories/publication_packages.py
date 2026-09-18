from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PublicationPackage, PublicationPackageVariant
from app.domain.enums import PackageStatus


class PublicationPackageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, package_id: UUID) -> PublicationPackage | None:
        return await self.session.get(PublicationPackage, package_id)

    async def list_by_property(
        self, property_id: UUID
    ) -> list[PublicationPackage]:
        rows = await self.session.scalars(
            select(PublicationPackage)
            .where(PublicationPackage.property_id == property_id)
            .order_by(PublicationPackage.created_at.desc())
        )
        return list(rows)

    async def get_latest_approved(
        self, property_id: UUID
    ) -> PublicationPackage | None:
        return cast(
            PublicationPackage | None,
            await self.session.scalar(
                select(PublicationPackage)
                .where(
                    PublicationPackage.property_id == property_id,
                    PublicationPackage.status == PackageStatus.APPROVED.value,
                )
                .order_by(PublicationPackage.updated_at.desc())
                .limit(1)
            ),
        )

    async def list_variants(
        self, package_id: UUID
    ) -> list[PublicationPackageVariant]:
        rows = await self.session.scalars(
            select(PublicationPackageVariant)
            .where(PublicationPackageVariant.package_id == package_id)
            .order_by(PublicationPackageVariant.created_at.asc())
        )
        return list(rows)

    async def create_package(
        self,
        *,
        property_id: UUID,
        property_fingerprint: str,
        status: str = PackageStatus.DRAFT.value,
    ) -> PublicationPackage:
        package = PublicationPackage(
            property_id=property_id,
            property_fingerprint=property_fingerprint,
            status=status,
        )
        self.session.add(package)
        await self.session.commit()
        await self.session.refresh(package)
        return package

    async def create_variants(
        self,
        variants_data: list[dict[str, object]],
    ) -> list[PublicationPackageVariant]:
        created: list[PublicationPackageVariant] = []
        for data in variants_data:
            variant = PublicationPackageVariant(**data)
            self.session.add(variant)
            created.append(variant)
        await self.session.commit()
        for v in created:
            await self.session.refresh(v)
        return created

    async def approve_package(self, package: PublicationPackage) -> PublicationPackage:
        package.status = PackageStatus.APPROVED.value
        await self.session.commit()
        await self.session.refresh(package)
        return package
