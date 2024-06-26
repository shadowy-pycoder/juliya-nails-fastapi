from datetime import date, datetime, time, timedelta
from uuid import UUID

import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.dialects.postgresql import UUID as pg_UUID

from src.models.base import BaseDBModel, association_table
from src.models.services import Service
from src.models.users import User


class Entry(BaseDBModel):
    __tablename__ = 'entry'

    services: so.Mapped[list['Service']] = so.relationship(
        secondary=association_table, back_populates='entries', lazy='selectin'
    )
    date: so.Mapped['date'] = so.mapped_column(sa.Date, nullable=False)
    time: so.Mapped['time'] = so.mapped_column(sa.Time, nullable=False)
    user_id: so.Mapped[UUID] = so.mapped_column(
        pg_UUID(as_uuid=True), sa.ForeignKey('user.uuid', ondelete='CASCADE', onupdate='CASCADE'), nullable=False
    )
    user: so.Mapped['User'] = so.relationship(back_populates='entries', lazy='joined', innerjoin=True)
    completed: so.Mapped[bool] = so.mapped_column(nullable=False, default=False, server_default='false')

    @property
    def timestamp(self) -> float:
        return datetime.combine(self.date, self.time).timestamp()

    @property
    def duration(self) -> int:
        return sum(service.duration for service in self.services)

    @property
    def ending_time(self) -> float:
        return self.timestamp + timedelta(minutes=self.duration).total_seconds()

    def __repr__(self) -> str:
        return f'Entry({self.uuid}, {self.date}, {self.time}, {self.user})'
