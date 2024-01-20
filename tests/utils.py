import io
from datetime import date, datetime, time, timedelta, timezone
from random import randint
from typing import Any, AsyncGenerator, Callable, Coroutine, TypeAlias
from uuid import UUID

from cryptography.fernet import Fernet
from httpx import AsyncClient
from passlib.hash import bcrypt
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import config
from src.models.entries import Entry
from src.models.posts import Post
from src.models.socials import SocialMedia
from src.models.users import User
from src.schemas.auth import Token

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


def create_test_image(*, fmt: str, size: int = config.IMAGE_SIZE) -> io.BytesIO:
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
