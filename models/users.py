from datetime import datetime
from typing import TYPE_CHECKING

from passlib.hash import bcrypt
import sqlalchemy as sa
import sqlalchemy.orm as so

from models.base import BaseDBModel

if TYPE_CHECKING:
    from models.socials import SocialMedia
    from models.posts import Post


class User(BaseDBModel):
    __tablename__ = 'user'

    email: so.Mapped[str] = so.mapped_column(sa.String(100), unique=True, nullable=False, index=True)
    hashed_password: so.Mapped[str] = so.mapped_column(sa.String(60), nullable=False)
    username: so.Mapped[str] = so.mapped_column(sa.String(20), unique=True, nullable=False, index=True)
    confirmed: so.Mapped[bool] = so.mapped_column(nullable=False, default=False, server_default='false')
    confirmed_on: so.Mapped[datetime] = so.mapped_column(sa.DateTime(timezone=True), nullable=True)
    active: so.Mapped[bool] = so.mapped_column(nullable=False, default=True, server_default='true')
    admin: so.Mapped[bool] = so.mapped_column(nullable=False, default=False)
    posts: so.WriteOnlyMapped['Post'] = so.relationship(
        back_populates='author', cascade="all, delete-orphan", passive_deletes=True
    )
    socials: so.Mapped['SocialMedia'] = so.relationship(back_populates='user', cascade="all, delete-orphan", lazy='joined')

    @property
    def password(self) -> None:
        raise AttributeError('Password is not a readable attribute')

    @password.setter
    def password(self, candidate: str) -> None:
        self.hashed_password = bcrypt.hash(candidate)
