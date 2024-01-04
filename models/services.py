from decimal import Decimal
from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as so

from models.base import BaseDBModel, association_table

if TYPE_CHECKING:
    from models.entries import Entry


class Service(BaseDBModel):
    __tablename__ = 'service'

    name: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True, nullable=False)
    duration: so.Mapped[Decimal] = so.mapped_column(sa.Numeric(scale=1), nullable=False)
    entries: so.WriteOnlyMapped['Entry'] = so.relationship(
        secondary=association_table, back_populates='services', passive_deletes=True
    )
