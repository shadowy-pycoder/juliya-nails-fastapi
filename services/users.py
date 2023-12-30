import sqlalchemy as sa

from .base import BaseService
from models.users import User
from schemas.users import UserRead, UserCreate, UserUpdate, UserUpdatePartial, UserAdminUpdate, UserAdminUpdatePartial, UserFilter


class UserService(
    BaseService[User, UserRead, UserCreate, UserUpdate, UserUpdatePartial, UserAdminUpdate, UserAdminUpdatePartial, UserFilter]
):
    model = User
    schema = UserRead
    filter_type = UserFilter

    async def verify_username(self, value: str) -> str:
        user = await self.session.scalar(sa.select(User).filter(User.username.ilike(value)))
        return 'Please choose a different username' if user else ''

    async def verify_email(self, value: str) -> str:
        user = await self.session.scalar(sa.select(User).filter(User.email.ilike(value)))
        return 'Please choose a different email' if user else ''
