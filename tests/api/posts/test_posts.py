from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import config
from src.models.posts import Post
from src.models.users import User
from src.schemas.auth import Token
from src.schemas.posts import PostRead
from src.utils import ImageType
from tests.utils import ImageFactory, PostFactory, create_temp_image


async def test_create_one(
    admin_user_token: Token,
    verified_user_token: Token,
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    img = create_temp_image()
    data = {'title': 'test_title', 'content': 'test_content'}
    resp = await async_client.post(
        'posts',
        data=data,
        files={'image': (img.name, img, 'image/png')},
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    resp_data = PostRead(**resp.json())
    assert str(resp_data.uuid) in resp.headers['Location']
    img_path = config.ROOT_DIR / config.UPLOAD_DIR / ImageType.POSTS.value / resp_data.image
    assert Path.exists(img_path)
    post = await async_session.scalar(sa.select(Post).filter_by(uuid=resp_data.uuid))
    assert post is not None
    Path.unlink(img_path)
    resp = await async_client.post(
        'posts',
        data=data,
        files={'image': (img.name, img, 'image/png')},
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('post_factory, expected', [(5, 5)], indirect=['post_factory'])
async def test_get_all(
    admin_user: User,
    admin_user_token: Token,
    post_factory: PostFactory,
    expected: int,
    async_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    await post_factory(admin_user, async_session)
    resp = await async_client.get(
        'posts', headers={'Authorization': f'Bearer {admin_user_token.access_token}'}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()['total'] == expected


@pytest.mark.parametrize('post_factory', [(1)], indirect=True)
async def test_get_one(
    admin_user: User,
    admin_user_token: Token,
    post_factory: PostFactory,
    async_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    posts = await post_factory(admin_user, async_session)
    resp = await async_client.get(
        f'posts/{posts[0].uuid}',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()['uuid'] == str(posts[0].uuid)
    assert resp.json()['author']['uuid'] == str(admin_user.uuid)


@pytest.mark.parametrize('image_factory', [('posts')], indirect=True)
async def test_get_post_image(
    admin_user: User,
    admin_user_token: Token,
    image_factory: ImageFactory[Post],
    async_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    data = {'title': 'test_title', 'content': 'test_content', 'author_id': admin_user.uuid}
    filename, img_path, post = await image_factory(
        instance=Post(**data), async_session=async_session
    )
    resp = await async_client.get(
        f'posts/{post.uuid}/image',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert Path.exists(img_path)
    Path.unlink(img_path)


@pytest.mark.parametrize('image_factory', [('posts')], indirect=True)
async def test_update_one(
    admin_user: User,
    admin_user_token: Token,
    verified_user_token: Token,
    image_factory: ImageFactory[Post],
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    old_data = {'title': 'test_title', 'content': 'test_content', 'author_id': admin_user.uuid}
    old_filename, old_img_path, post = await image_factory(
        instance=Post(**old_data), async_session=async_session
    )
    img = create_temp_image()
    new_data = {'title': 'new_test_title', 'content': 'new_test_content'}
    resp = await async_client.put(
        f'posts/{post.uuid}',
        data=new_data,
        files={'image': (img.name, img, 'image/png')},
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = PostRead(**resp.json())
    await async_session.refresh(post)
    assert post.image == resp_data.image
    assert post.title == resp_data.title
    assert resp_data.image != old_filename
    assert Path.exists(old_img_path.parent / resp_data.image)
    assert not Path.exists(old_img_path)
    Path.unlink(old_img_path.parent / resp_data.image)
    resp = await async_client.put(
        f'posts/{post.uuid}',
        data=new_data,
        files={'image': (img.name, img, 'image/png')},
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('image_factory', [('posts')], indirect=True)
async def test_patch_one(
    admin_user: User,
    admin_user_token: Token,
    verified_user_token: Token,
    image_factory: ImageFactory[Post],
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    old_data = {'title': 'test_title', 'content': 'test_content', 'author_id': admin_user.uuid}
    old_filename, old_img_path, post = await image_factory(
        instance=Post(**old_data), async_session=async_session
    )
    new_data = {'title': 'new_test_title', 'content': 'new_test_content'}
    resp = await async_client.patch(
        f'posts/{post.uuid}',
        data=new_data,
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_200_OK
    resp_data = PostRead(**resp.json())
    await async_session.refresh(post)
    assert resp_data.image == old_filename
    assert resp_data.title == new_data['title']
    assert post.image == old_filename
    assert post.title == new_data['title']
    assert Path.exists(old_img_path)
    Path.unlink(old_img_path)
    resp = await async_client.patch(
        f'posts/{post.uuid}',
        data=new_data,
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize('image_factory', [('posts')], indirect=True)
async def test_delete_one(
    admin_user: User,
    admin_user_token: Token,
    verified_user_token: Token,
    image_factory: ImageFactory[Post],
    async_client: AsyncClient,
    async_session: AsyncSession,
) -> None:
    data = {'title': 'test_title', 'content': 'test_content', 'author_id': admin_user.uuid}
    filename, img_path, post = await image_factory(
        instance=Post(**data), async_session=async_session
    )
    resp = await async_client.delete(
        f'posts/{post.uuid}',
        headers={'Authorization': f'Bearer {admin_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    result = await async_session.scalar(sa.select(Post).filter_by(uuid=post.uuid))
    assert result is None
    assert not Path.exists(img_path)
    resp = await async_client.delete(
        f'posts/{post.uuid}',
        headers={'Authorization': f'Bearer {verified_user_token.access_token}'},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
