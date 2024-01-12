from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as so

from src.models.base import BaseDBModel, association_table

if TYPE_CHECKING:
    from src.models.entries import Entry


class Service(BaseDBModel):
    __tablename__ = 'service'

    name: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True, nullable=False)
    duration: so.Mapped[int] = so.mapped_column(sa.Integer, nullable=False)
    entries: so.WriteOnlyMapped['Entry'] = so.relationship(
        secondary=association_table, back_populates='services', passive_deletes=True
    )
