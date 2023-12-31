from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
import sqlalchemy.orm as so

from models.base import BaseDBModel, association_table
from models.services import Service
from models.users import User


class Entry(BaseDBModel):
    __tablename__ = 'entry'

    services: so.Mapped[list['Service']] = so.relationship(secondary=association_table, back_populates='entries', lazy='joined')
    date: so.Mapped['date'] = so.mapped_column(sa.Date, nullable=False)
    time: so.Mapped['time'] = so.mapped_column(sa.Time(timezone=True), nullable=False)
    user_id: so.Mapped[UUID] = so.mapped_column(
        pg_UUID(as_uuid=True), sa.ForeignKey('user.uuid', ondelete='CASCADE'), nullable=False
    )
    user: so.Mapped['User'] = so.relationship(back_populates='entries')
    completed: so.Mapped[bool] = so.mapped_column(nullable=False, default=False, server_default='false')

    @property
    def timestamp(self) -> float:
        return datetime.combine(self.date, self.time).timestamp()

    @property
    def duration(self) -> Decimal | Literal[0]:
        return sum(service.duration for service in self.services)

    @property
    def ending_time(self) -> float:
        return self.timestamp + timedelta(hours=float(self.duration)).total_seconds()
