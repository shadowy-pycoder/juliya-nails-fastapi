from contextlib import nullcontext as does_not_raise, AbstractContextManager
from pathlib import Path
import tempfile
from typing import Any

from fastapi import HTTPException, UploadFile
import pytest
from starlette.datastructures import Headers

from src.core.config import config
from src.utils import (
    check_password_strength,
    MESSAGE_PREFIX,
    get_url,
    ImageType,
    get_image,
    save_image,
    delete_image,
)
from tests.utils import VERSION, create_test_image


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


@pytest.mark.parametrize('image_type', [('posts'), ('profiles')])
async def test_save_image(image_type: str) -> None:
    img = create_test_image(fmt='png')
    filename = await save_image(
        UploadFile(img, headers=Headers({'Content-Type': 'image/png'})), path=ImageType(image_type)
    )
    img_path = config.ROOT_DIR / config.UPLOAD_DIR / ImageType(image_type).value / filename
    assert Path.exists(img_path)
    Path.unlink(img_path)


@pytest.mark.parametrize('image_type', [('posts'), ('profiles')])
async def test_save_image_too_large(image_type: str) -> None:
    img = create_test_image(fmt='png', size=config.IMAGE_SIZE + 1)
    with pytest.raises(HTTPException):
        await save_image(
            UploadFile(img, headers=Headers({'Content-Type': 'image/png'})),
            path=ImageType(image_type),
        )


@pytest.mark.parametrize('image_type', [('posts'), ('profiles')])
async def test_delete_image(image_type: str) -> None:
    img = create_test_image(fmt='png')
    filename = await save_image(
        UploadFile(img, headers=Headers({'Content-Type': 'image/png'})), path=ImageType(image_type)
    )
    img_path = config.ROOT_DIR / config.UPLOAD_DIR / ImageType(image_type).value / filename
    assert Path.exists(img_path)
    delete_image(filename, path=ImageType(image_type))
    assert not Path.exists(img_path)
