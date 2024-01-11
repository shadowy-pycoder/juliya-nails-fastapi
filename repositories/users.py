from typing import TypeAlias, TYPE_CHECKING

from fastapi.background import BackgroundTasks

from models.users import User
from repositories.base import BaseRepository
from schemas.users import (
    UserRead,
    UserCreate,
    UserUpdate,
    UserUpdatePartial,
    UserAdminUpdate,
    UserAdminUpdatePartial,
    UserFilter,
)

if TYPE_CHECKING:
    from repositories.auth import AuthRepository


UserSchema: TypeAlias = UserUpdate | UserUpdatePartial | UserAdminUpdate | UserAdminUpdatePartial


class UserRepository(
    BaseRepository[
        User,
        UserRead,
        UserCreate,
        UserUpdate,
        UserUpdatePartial,
        UserAdminUpdate,
        UserAdminUpdatePartial,
        UserFilter,
    ]
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
        return await super().update(
            user, values, exclude_unset=exclude_unset, exclude_none=exclude_none
        )

    async def update_with_confirmation(
        self,
        user: User,
        values: UserUpdate | UserUpdatePartial,
        auth_repo: 'AuthRepository',
        background_tasks: BackgroundTasks,
        exclude_unset: bool = False,
        exclude_none: bool = False,
    ) -> User:
        new_values: UserAdminUpdatePartial | None = None
        await self.verify_uniqueness(values, ['username', 'email'], user)
        if values.email is not None and values.email != user.email:
            new_values = UserAdminUpdatePartial(
                **values.model_dump(exclude_unset=True),
                confirmed=False,
                confirmed_on=None,
            )
            user = await super().update(
                user, new_values, exclude_unset=exclude_unset, exclude_none=exclude_none
            )
            await auth_repo.change_email(user, background_tasks)
            return user
        return await super().update(
            user, values, exclude_unset=exclude_unset, exclude_none=exclude_none
        )
