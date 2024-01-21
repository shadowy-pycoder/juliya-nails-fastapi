import tempfile
from contextlib import AbstractContextManager
from contextlib import nullcontext as does_not_raise
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

from src.core.config import config
from src.utils import (
    MESSAGE_PREFIX,
    ImageType,
    check_password_strength,
    delete_image,
    get_image,
    get_url,
)
from tests.utils import VERSION, ImageFactory


@pytest.mark.parametrize(
    'password, expectation',
    [
        ('foo#Bar34', does_not_raise()),
        ('foo#BarTest', pytest.raises(ValueError, match=f'{MESSAGE_PREFIX}1 digit')),
        (
            '123456789',
            pytest.raises(
                ValueError, match=f'{MESSAGE_PREFIX}1 uppercase, 1 lowercase, 1 special character'
            ),
        ),
        ('foobar3#', pytest.raises(ValueError, match=f'{MESSAGE_PREFIX}1 uppercase')),
        ('BAR#$123', pytest.raises(ValueError, match=f'{MESSAGE_PREFIX}1 lowercase')),
    ],
)
def test_check_password_strength(
    password: str,
    expectation: AbstractContextManager[Any],
) -> None:
    with expectation:
        check_password_strength(password)


@pytest.mark.parametrize(
    'module',
    [('users'), ('entries'), ('posts'), ('services'), ('socials')],
)
def test_get_url(module: str) -> None:
    UUID = 'b47b2559-646e-487a-b377-370d15f27835'
    assert get_url(module, uuid=UUID) == f'/{VERSION}{module}/{UUID}'


@pytest.mark.parametrize('image_type', [('posts'), ('profiles')])
def test_get_image(image_type: str) -> None:
    img_path = config.ROOT_DIR / config.UPLOAD_DIR / ImageType(image_type).value
    with tempfile.NamedTemporaryFile(suffix='.jpg', dir=img_path) as temp_file:
        assert get_image(temp_file.name, path=ImageType(image_type)) == img_path / temp_file.name
    with pytest.raises(HTTPException):
        get_image('test', path=ImageType(image_type))


@pytest.mark.parametrize('populate_image', [('posts'), ('profiles')], indirect=True)
async def test_save_image(populate_image: ImageFactory) -> None:
    filename, img_path = await populate_image()
    assert Path.exists(img_path)
    Path.unlink(img_path)


@pytest.mark.parametrize('populate_image', [('posts'), ('profiles')], indirect=True)
async def test_save_image_too_large(populate_image: ImageFactory) -> None:
    with pytest.raises(HTTPException):
        await populate_image(size=config.IMAGE_SIZE + 1)


@pytest.mark.parametrize(
    'populate_image, image_type',
    [('posts', 'posts'), ('profiles', 'profiles')],
    indirect=['populate_image'],
)
async def test_delete_image(populate_image: ImageFactory, image_type: str) -> None:
    filename, img_path = await populate_image()
    assert Path.exists(img_path)
    delete_image(filename, path=ImageType(image_type))
    assert not Path.exists(img_path)
