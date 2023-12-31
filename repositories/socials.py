from pathlib import Path

from fastapi import UploadFile

from config import config
from models.socials import SocialMedia
from schemas.socials import (
    SocialRead,
    SocialCreate,
    SocialUpdate,
    SocialUpdatePartial,
    SocialAdminUpdate,
    SocialAdminUpdatePartial,
    SocialFilter,
)
from repositories.base import BaseRepository
from utils import get_image, save_image, delete_image


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
        return get_image(socials.avatar, path='profiles')

    async def update_avatar(self, socials: SocialMedia, file: UploadFile) -> None:
        old_avatar = socials.avatar
        socials.avatar = await save_image(file, path='profiles')
        self.session.add(socials)
        await self.session.commit()
        await self.session.refresh(socials)
        delete_image(old_avatar, path='profiles')

    async def delete_avatar(self, socials: SocialMedia) -> None:
        delete_image(socials.avatar, path='profiles')
        socials.avatar = config.DEFAULT_AVATAR
        self.session.add(socials)
        await self.session.commit()
        await self.session.refresh(socials)
