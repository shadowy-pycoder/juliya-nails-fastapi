from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
import sqlalchemy.orm as so
from sqlalchemy.sql import func

from database import Base

association_table = sa.Table(
    'association_table',
    Base.metadata,
    sa.Column('entry_id', pg_UUID(as_uuid=True), sa.ForeignKey('entry.uuid', ondelete='CASCADE')),
    sa.Column(
        'service_id', pg_UUID(as_uuid=True), sa.ForeignKey('service.uuid', ondelete='SET NULL')
    ),
)


class BaseDBModel(Base):
    __abstract__ = True

    uuid: so.Mapped[UUID] = so.mapped_column(pg_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            k: v for k, v in self.__dict__.items() if not k.startswith('__') and not callable(k)
        }

    def update(self, data: dict[str, Any]) -> None:
        for attr, value in data.items():
            setattr(self, attr, value)
