from typing import TYPE_CHECKING, TypeAlias

from fastapi.background import BackgroundTasks
from fastapi.logger import logger

from src.models.users import User
from src.repositories.base import BaseRepository
from src.schemas.users import (
    UserAdminUpdate,
    UserAdminUpdatePartial,
    UserCreate,
    UserFilter,
    UserRead,
    UserUpdate,
    UserUpdatePartial,
)


if TYPE_CHECKING:
    from src.repositories.auth import AuthRepository


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
        exclude_defaults: bool = False,
    ) -> User:
        await self.verify_uniqueness(values, ['username', 'email'], user)
        return await super().update(
            user,
            values,
            exclude_unset=exclude_unset,
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
        )

    async def update_with_confirmation(
        self,
        user: User,
        values: UserUpdate | UserUpdatePartial,
        auth_repo: 'AuthRepository',
        background_tasks: BackgroundTasks,
        exclude_unset: bool = False,
        exclude_none: bool = False,
        exclude_defaults: bool = False,
    ) -> User:
        await self.verify_uniqueness(values, ['username', 'email'], user)

        if values.email is not None and values.email != user.email:
            new_values = UserAdminUpdatePartial(
                **values.model_dump(exclude_unset=True),
                confirmed=False,
                confirmed_on=None,
                active=user.active,
                admin=user.admin,
                created=user.created,
            )
            user = await super().update(
                user,
                new_values,
                exclude_unset=exclude_unset,
                exclude_none=exclude_none,
                exclude_defaults=exclude_defaults,
            )
            await auth_repo.change_email(user, background_tasks)
            logger.info(f'[change email request]: {user}')
            return user
        return await super().update(
            user,
            values,
            exclude_unset=exclude_unset,
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
        )
