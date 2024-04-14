import io
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from random import randint
from typing import Any, AsyncGenerator, Callable, Coroutine, TypeAlias, TypeVar
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
from src.models.services import Service
from src.models.socials import SocialMedia
from src.models.users import User
from src.schemas.auth import Token
from src.utils import ImageType, save_image


VERSION = 'api/v1/'

BASE_URL = f'http://testserver/{VERSION}'

ADMIN_USER = {
    'uuid': UUID('5ad22093-194e-429c-b2af-cb531c7267c1'),
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
    'uuid': UUID('950f8c5f-ad0c-4fb7-a693-dc42c7ea453a'),
    'email': 'alice@alice.com',
    'password': 'alice',
    'hashed_password': bcrypt.hash('alice'),
    'username': 'alice',
    'confirmed': True,
    'confirmed_on': datetime.now(tz=timezone.utc),
    'active': True,
    'admin': False,
}

SECOND_VERIFIED_USER = {
    'uuid': UUID('aa61807e-2490-4c09-ba09-4f4754840e5c'),
    'email': 'john@john.com',
    'password': 'john',
    'hashed_password': bcrypt.hash('john'),
    'username': 'john',
    'confirmed': True,
    'confirmed_on': datetime.now(tz=timezone.utc),
    'active': True,
    'admin': False,
}
UNVERIFIED_USER = {
    'uuid': UUID('764a3113-7d87-4345-8c91-d68e2464b060'),
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
    'uuid': UUID('a1685c3b-1034-4b75-ad8c-16c8a3408cab'),
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
    'uuid': UUID('a498e5d0-d145-478d-a21c-a480209addb1'),
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

SOCIAL_DATA = {
    'first_name': 'John',
    'last_name': 'Doe',
    'phone_number': '+9 999 999 99 99',
    'viber': '+9 999 999 99 99',
    'whatsapp': '+9 999 999 99 99',
    'instagram': 'instagram.com/john_doe',
    'telegram': 'https://t.me/john_doe',
    'youtube': 'https://www.youtube.com/channel/john_doe/',
    'website': 'https://www.example.com/',
    'vk': 'https://vk.com/john_doe',
    'about': 'My name is John Doe',
}

SERVICES = [
    {'uuid': UUID('e1c9ae56-c592-4fdb-a880-f567e1d0d75b'), 'name': 'Service 1', 'duration': 10},
    {'uuid': UUID('729c1c06-29ec-4058-be9d-e1b543da9794'), 'name': 'Service 2', 'duration': 30},
    {'uuid': UUID('4b5d4ed3-033b-4ccb-82ed-304cd04ff79b'), 'name': 'Service 3', 'duration': 60},
    {'uuid': UUID('7037d2a2-10e4-4d91-abd0-5cca14c35ec7'), 'name': 'Service 4', 'duration': 90},
    {'uuid': UUID('e9b13e10-ad34-4716-a46e-c4f989844fe7'), 'name': 'Service 5', 'duration': 120},
]

POSTS = [
    {
        'uuid': UUID('e88dcfad-54d8-4f09-949c-ed529dd26dd1'),
        'title': 'title 1',
        'image': 'image1.jpg',
        'content': 'content 1',
        'author_id': ADMIN_USER['uuid'],
    },
    {
        'uuid': UUID('5e3c1308-b798-42ca-a383-2e4cc8f0cf8a'),
        'title': 'title 2',
        'image': 'image2.jpg',
        'content': 'content 2',
        'author_id': ADMIN_USER['uuid'],
    },
    {
        'uuid': UUID('d61d71b3-d4cc-4f29-994d-072b06f26a17'),
        'title': 'title 3',
        'image': 'image3.jpg',
        'content': 'content 3',
        'author_id': ADMIN_USER['uuid'],
    },
    {
        'uuid': UUID('752ff446-8190-4ed6-9c5d-ff23a5f0fb7c'),
        'title': 'title 4',
        'image': 'image4.jpg',
        'content': 'content 4',
        'author_id': ADMIN_USER['uuid'],
    },
    {
        'uuid': UUID('3b7959eb-d397-4242-895d-8b50891ff32a'),
        'title': 'title 5',
        'image': 'image5.jpg',
        'content': 'content 5',
        'author_id': ADMIN_USER['uuid'],
    },
]

T = TypeVar('T', User, Post, None)
EntryFactory: TypeAlias = Callable[[User, AsyncSession], Coroutine[Any, Any, AsyncGenerator[list[Entry], None]]]
ImageFactory: TypeAlias = Callable[..., Coroutine[Any, Any, AsyncGenerator[tuple[str, Path, T], None]]]
EntryList = tuple[dict[str, Any], dict[str, Any], dict[str, Any], datetime]


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


async def create_entries(user_id: UUID, count: int, async_session: AsyncSession) -> AsyncGenerator[list[Entry], None]:
    entries = []
    services = [Service(**data) for data in SERVICES]
    for _ in range(count):
        entry_date = date.today() + timedelta(days=randint(14, 28))
        entry_time = time(hour=randint(0, 23), minute=randint(0, 59))
        entries.append(
            Entry(
                date=entry_date,
                time=entry_time,
                services=services[randint(0, len(services) - 1) :],
                user_id=user_id,
            )
        )
    async_session.add_all(entries)
    async_session.add_all(services)
    await async_session.commit()
    yield entries
    for entry in entries:
        await async_session.delete(entry)
    for service in services:
        await async_session.delete(service)
    await async_session.commit()


async def create_image(
    fmt: str,
    image_type: str,
    size: int,
    instance: T,
    async_session: AsyncSession | None = None,
) -> AsyncGenerator[tuple[str, Path, T], None]:
    img = create_temp_image(fmt=fmt, size=size)
    filename = await save_image(
        UploadFile(img, headers=Headers({'Content-Type': f'image/{fmt}'}), filename=img.name),
        path=ImageType(image_type),
    )
    img_path = config.ROOT_DIR / config.UPLOAD_DIR / ImageType(image_type).value / filename
    if async_session is not None:
        if isinstance(instance, User):
            social = (await async_session.execute(sa.select(SocialMedia).filter_by(user_id=instance.uuid))).scalar_one()
            social.avatar = filename
            async_session.add(instance)
            await async_session.commit()
            await async_session.refresh(instance)
            await async_session.refresh(social)
        elif isinstance(instance, Post):
            instance.image = filename
            async_session.add(instance)
            await async_session.commit()
            await async_session.refresh(instance)
    yield filename, img_path, instance
    Path.unlink(img_path, missing_ok=True)
