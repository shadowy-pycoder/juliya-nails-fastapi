from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as pg_UUID
import sqlalchemy.orm as so

from src.models.base import BaseDBModel
from src.models.users import User


class SocialMedia(BaseDBModel):
    __tablename__ = 'social'

    user_id: so.Mapped[UUID] = so.mapped_column(
        pg_UUID(as_uuid=True), sa.ForeignKey('user.uuid', ondelete='CASCADE'), nullable=False
    )
    user: so.Mapped[User] = so.relationship(back_populates='socials', lazy='joined')
    avatar: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False, default='default.jpg')
    first_name: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=True)
    last_name: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=True)
    phone_number: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, nullable=True)
    viber: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, nullable=True)
    whatsapp: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, nullable=True)
    instagram: so.Mapped[str] = so.mapped_column(sa.String(255), unique=True, nullable=True)
    telegram: so.Mapped[str] = so.mapped_column(sa.String(255), unique=True, nullable=True)
    youtube: so.Mapped[str] = so.mapped_column(sa.String(255), unique=True, nullable=True)
    website: so.Mapped[str] = so.mapped_column(sa.String(255), unique=True, nullable=True)
    vk: so.Mapped[str] = so.mapped_column(sa.String(255), unique=True, nullable=True)
    about: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=True)

    def __repr__(self) -> str:
        return f'SocialMedia({self.uuid}, {self.user})'
