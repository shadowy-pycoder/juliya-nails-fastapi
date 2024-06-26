from pathlib import Path
from typing import TypeAlias

from fastapi import UploadFile

from src.models.posts import Post
from src.repositories.base import BaseRepository
from src.schemas.posts import (
    PostAdminUpdate,
    PostAdminUpdatePartial,
    PostCreate,
    PostFilter,
    PostRead,
    PostUpdate,
    PostUpdatePartial,
)
from src.utils import ImageType, delete_image, get_image, save_image


PostUpdateSchema: TypeAlias = PostUpdate | PostUpdatePartial | PostAdminUpdate | PostAdminUpdatePartial


class PostRepository(
    BaseRepository[
        Post,
        PostRead,
        PostCreate,
        PostUpdate,
        PostUpdatePartial,
        PostAdminUpdate,
        PostAdminUpdatePartial,
        PostFilter,
    ]
):
    model = Post
    schema = PostRead
    filter_type = PostFilter

    def get_post_image(self, post: Post) -> Path:
        return get_image(post.image, path=ImageType.POSTS)

    async def save_post_image(self, file: UploadFile) -> str:
        return await save_image(file, path=ImageType.POSTS)

    async def create(self, values: PostCreate) -> Post:
        await self.verify_uniqueness(values, ['title'])
        return await super().create(values)

    async def update(
        self,
        post: Post,
        values: PostUpdateSchema,
        exclude_unset: bool = False,
        exclude_none: bool = False,
        exclude_defaults: bool = False,
    ) -> Post:
        await self.verify_uniqueness(values, ['title'], post)
        old_post_image = post.image
        result = await super().update(
            post,
            values,
            exclude_unset=exclude_unset,
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
        )
        if values.image is not None:
            delete_image(old_post_image, path=ImageType.POSTS)
        return result

    async def delete(self, post: Post) -> None:
        old_post_image = post.image
        await super().delete(post)
        delete_image(old_post_image, path=ImageType.POSTS)
