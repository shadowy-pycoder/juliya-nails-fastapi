from uuid import UUID

import sqlalchemy as sa
import sqlalchemy.orm as so
from sqlalchemy.dialects.postgresql import UUID as pg_UUID

from src.models.base import BaseDBModel
from src.models.users import User


class Post(BaseDBModel):
    __tablename__ = 'post'

    title: so.Mapped[str] = so.mapped_column(sa.String(100), unique=True, nullable=False)
    image: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    content: so.Mapped[str] = so.mapped_column(sa.Text, nullable=False)
    author_id: so.Mapped[UUID] = so.mapped_column(
        pg_UUID(as_uuid=True), sa.ForeignKey('user.uuid', ondelete='CASCADE', onupdate='CASCADE'), nullable=False
    )
    author: so.Mapped['User'] = so.relationship(back_populates='posts', lazy='joined', innerjoin=True)

    def __repr__(self) -> str:
        return f'Post({self.uuid}, {self.title}, {self.author})'
