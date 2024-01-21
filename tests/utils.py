import io
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from random import randint
from typing import Any, AsyncGenerator, Callable, Coroutine, TypeAlias
from uuid import UUID

import sqlalchemy as sa
from cryptography.fernet import Fernet
from fastapi import UploadFile
from httpx import AsyncClient
from passlib.hash import bcrypt
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from src.core.config import config
from src.models.entries import Entry
from src.models.posts import Post
from src.models.socials import SocialMedia
from src.models.users import User
from src.schemas.auth import Token
from src.utils import ImageType, save_image

VERSION = 'api/v1/'

BASE_URL = f'http://testserver/{VERSION}'

ADMIN_USER = {
    'uuid': '5ad22093-194e-429c-b2af-cb531c7267c1',
    'email': 'admin@admin.com',
    'password': 'admin',
    'hashed_password': bcrypt.hash('admin'),
    'username': 'admin',
    'confirmed': True,
    'confirmed_on': datetime.now(tz=timezone.utc),
    'active': True,
    'admin': True,
}
VERIFIED_USER = {
    'uuid': '950f8c5f-ad0c-4fb7-a693-dc42c7ea453a',
    'email': 'alice@alice.com',
    'password': 'alice',
    'hashed_password': bcrypt.hash('alice'),
    'username': 'alice',
    'confirmed': True,
    'confirmed_on': datetime.now(tz=timezone.utc),
    'active': True,
    'admin': False,
}
UNVERIFIED_USER = {
    'uuid': '764a3113-7d87-4345-8c91-d68e2464b060',
    'email': 'bob@bob.com',
    'password': 'bob',
    'hashed_password': bcrypt.hash('bob'),
    'username': 'bob',
    'confirmed': False,
    'confirmed_on': None,
    'active': False,
    'admin': False,
}
INACTIVE_USER = {
    'uuid': 'a1685c3b-1034-4b75-ad8c-16c8a3408cab',
    'email': 'chuck@chuck.com',
    'password': 'chuck',
    'hashed_password': bcrypt.hash('chuck'),
    'username': 'chuck',
    'confirmed': True,
    'confirmed_on': datetime.now(tz=timezone.utc),
    'active': False,
    'admin': False,
}
ANONYMOUS_USER = {
    'uuid': 'a498e5d0-d145-478d-a21c-a480209addb1',
    'username': 'anonymous',
    'email': 'anon@anon.com',
    'password': 'anonymous',
}

USER_DATA = {
    'username': 'carol',
    'email': 'carol@carol.com',
    'password': 'carol#3C',
    'confirm_password': 'carol#3C',
}


EntryFactory: TypeAlias = Callable[[User, AsyncSession], Coroutine[Any, Any, list[Entry]]]
PostFactory: TypeAlias = Callable[[User, AsyncSession], Coroutine[Any, Any, list[Post]]]
ImageFactory: TypeAlias = Callable[..., Coroutine[Any, Any, tuple[str, Path]]]


def parse_payload(payload: list[Any]) -> str | None:
    msg_split: list[bytes] = payload[0]._payload[0].get_payload(decode=True).split(b'/')
    for msg in msg_split:
        if msg.startswith(b'eyJ'):
            return msg.split(b'"')[0].decode('utf-8')
    return None


class TokenHandler:
    fernet = Fernet(config.SECRET_KEY)

    @classmethod
    def encrypt_token(cls, token: str) -> bytes:
        return cls.fernet.encrypt(token.encode('utf-8'))

    @classmethod
    def decrypt_token(cls, token: bytes) -> str:
        return cls.fernet.decrypt(token).decode('utf-8')


async def create_user(user_type: dict[str, Any], async_session: AsyncSession) -> User:
    user = User(**user_type)
    social = SocialMedia(user_id=user.uuid)
    async_session.add(user)
    async_session.add(social)
    await async_session.commit()
    return user


async def delete_user(user: User, async_session: AsyncSession) -> None:
    await async_session.delete(user)
    await async_session.commit()


async def create_token(user: User, user_type: dict[str, Any], async_client: AsyncClient) -> Token:
    data = {'username': user_type['username'], 'password': user_type['password']}
    resp = await async_client.post('auth/token', data=data)
    return Token.model_validate(resp.json())


def create_temp_image(*, fmt: str = 'png', size: int = config.IMAGE_SIZE) -> io.BytesIO:
    file = io.BytesIO(b'\0' * size)
    image = Image.new('RGB', size=(50, 50), color=(155, 0, 0))
    image.save(file, fmt)
    file.name = f'test.{fmt}'
    file.seek(0)
    return file


async def create_entries(
    user_id: UUID, count: int, async_session: AsyncSession
) -> AsyncGenerator[list[Entry], None]:
    entries = []
    for _ in range(count):
        entry_date = date.today() + timedelta(days=randint(0, 7))
        entry_time = time(hour=randint(0, 23), minute=randint(0, 59))
        entries.append(Entry(date=entry_date, time=entry_time, user_id=user_id))
    async_session.add_all(entries)
    await async_session.commit()
    yield entries
    await async_session.delete(entries)
    await async_session.commit()


async def create_posts(
    user_id: UUID, count: int, async_session: AsyncSession
) -> AsyncGenerator[list[Post], None]:
    posts = []
    for i in range(count):
        title = f'Post {i} by {user_id}'
        image = f'Image{i}.jpg'
        content = f'Content {i}'
        posts.append(Post(title=title, image=image, content=content, author_id=user_id))
    async_session.add_all(posts)
    await async_session.commit()
    yield posts
    await async_session.delete(posts)
    await async_session.commit()


async def create_image(
    fmt: str,
    image_type: str,
    size: int = config.IMAGE_SIZE,
    instance: SocialMedia | Post | None = None,
    async_session: AsyncSession | None = None,
) -> tuple[str, Path]:
    img = create_temp_image(fmt=fmt, size=size)
    filename = await save_image(
        UploadFile(img, headers=Headers({'Content-Type': f'image/{fmt}'}), filename=img.name),
        path=ImageType(image_type),
    )
    img_path = config.ROOT_DIR / config.UPLOAD_DIR / ImageType(image_type).value / filename
    if async_session is not None:
        if isinstance(instance, User):
            social = (
                await async_session.execute(sa.select(SocialMedia).filter_by(user_id=instance.uuid))
            ).scalar_one()
            social.avatar = filename
            await async_session.commit()
            await async_session.refresh(instance)
        elif isinstance(instance, Post):
            instance.image = filename
            await async_session.commit()
            await async_session.refresh(instance)
    return filename, img_path
