from typing import TypeAlias

from models.users import User
from repositories.base import BaseRepository
from schemas.users import UserRead, UserCreate, UserUpdate, UserUpdatePartial, UserAdminUpdate, UserAdminUpdatePartial, UserFilter

UserSchema: TypeAlias = UserUpdate | UserUpdatePartial | UserAdminUpdate | UserAdminUpdatePartial


class UserRepository(
    BaseRepository[User, UserRead, UserCreate, UserUpdate, UserUpdatePartial, UserAdminUpdate, UserAdminUpdatePartial, UserFilter]
):
    model = User
    schema = UserRead
    filter_type = UserFilter

    async def create(self, values: UserCreate) -> User:
        await self.verify_uniqueness(values, ['username', 'email'])
        return await super().create(values)

    async def update(
        self,
        user: User,
        values: UserSchema,
        exclude_unset: bool = False,
        exclude_none: bool = False,
    ) -> User:
        await self.verify_uniqueness(values, ['username', 'email'], user)
        return await super().update(user, values, exclude_unset=exclude_unset, exclude_none=exclude_none)
