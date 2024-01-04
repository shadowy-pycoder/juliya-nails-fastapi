from pathlib import Path
from typing import TypeAlias

from fastapi import UploadFile

from models.posts import Post
from schemas.posts import PostRead, PostCreate, PostUpdate, PostUpdatePartial, PostAdminUpdate, PostAdminUpdatePartial, PostFilter
from repositories.base import BaseRepository
from utils import get_image, save_image, delete_image

PostUpdateSchema: TypeAlias = PostUpdate | PostUpdatePartial | PostAdminUpdate | PostAdminUpdatePartial


class PostRepository(
    BaseRepository[Post, PostRead, PostCreate, PostUpdate, PostUpdatePartial, PostAdminUpdate, PostAdminUpdatePartial, PostFilter]
):
    model = Post
    schema = PostRead
    filter_type = PostFilter

    def get_post_image(self, post: Post) -> Path:
        return get_image(post.image)

    async def save_post_image(self, file: UploadFile) -> str:
        return await save_image(file)

    async def create(self, values: PostCreate) -> Post:
        await self.verify_uniqueness(values, ['title'])
        return await super().create(values)

    async def update(self, post: Post, values: PostUpdateSchema, exclude_unset: bool = False, exclude_none: bool = False) -> Post:
        await self.verify_uniqueness(values, ['title'], post)
        old_post_image = post.image
        result = await super().update(post, values, exclude_unset=exclude_unset, exclude_none=exclude_none)
        delete_image(old_post_image)
        return result

    async def delete(self, post: Post) -> None:
        old_post_image = post.image
        await super().delete(post)
        delete_image(old_post_image)
