from pathlib import Path

from fastapi import UploadFile

from src.core.config import config
from src.models.socials import SocialMedia
from src.repositories.base import BaseRepository
from src.schemas.socials import (
    SocialAdminUpdate,
    SocialAdminUpdatePartial,
    SocialCreate,
    SocialFilter,
    SocialRead,
    SocialUpdate,
    SocialUpdatePartial,
)
from src.utils import ImageType, delete_image, get_image, save_image


class SocialRepository(
    BaseRepository[
        SocialMedia,
        SocialRead,
        SocialCreate,
        SocialUpdate,
        SocialUpdatePartial,
        SocialAdminUpdate,
        SocialAdminUpdatePartial,
        SocialFilter,
    ]
):
    model = SocialMedia
    schema = SocialRead
    filter_type = SocialFilter

    def get_avatar(self, socials: SocialMedia) -> Path:
        return get_image(socials.avatar, path=ImageType.PROFILES)

    async def update_avatar(self, socials: SocialMedia, file: UploadFile) -> None:
        old_avatar = socials.avatar
        socials.avatar = await save_image(file, path=ImageType.PROFILES)
        self.session.add(socials)
        await self.session.commit()
        await self.session.refresh(socials)
        delete_image(old_avatar, path=ImageType.PROFILES)

    async def delete_avatar(self, socials: SocialMedia) -> None:
        delete_image(socials.avatar, path=ImageType.PROFILES)
        socials.avatar = config.DEFAULT_AVATAR
        self.session.add(socials)
        await self.session.commit()
        await self.session.refresh(socials)
