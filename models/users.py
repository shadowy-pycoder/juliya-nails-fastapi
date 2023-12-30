from datetime import datetime

from passlib.hash import bcrypt
import sqlalchemy as sa
import sqlalchemy.orm as so

from .base import BaseDBModel


class User(BaseDBModel):
    __tablename__ = 'user'

    email: so.Mapped[str] = so.mapped_column(sa.String(100), unique=True, nullable=False, index=True)
    hashed_password: so.Mapped[str] = so.mapped_column(sa.String(60), nullable=False)
    username: so.Mapped[str] = so.mapped_column(sa.String(20), unique=True, nullable=False, index=True)
    confirmed: so.Mapped[bool] = so.mapped_column(nullable=False, default=False)
    confirmed_on: so.Mapped[datetime] = so.mapped_column(sa.DateTime(timezone=True), nullable=True)
    admin: so.Mapped[bool] = so.mapped_column(nullable=False, default=False)

    @property
    def password(self) -> None:
        raise AttributeError('Password is not a readable attribute')

    @password.setter
    def password(self, candidate: str) -> None:
        self.hashed_password = bcrypt.hash(candidate)
