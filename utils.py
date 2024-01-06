from enum import Enum
from importlib import import_module
from io import BytesIO
from pathlib import Path
import re
import secrets
from typing import Any

import aiofiles
from fastapi import status, HTTPException, UploadFile, APIRouter
import filetype  # type: ignore[import-untyped]
from PIL import Image

from config import config

HTTP_403_FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not allowed to perform this operation')

PATTERNS = {
    'username': r'^[A-Za-z][A-Za-z0-9_.]*$',
    'youtube': r'(https?:\/\/)?(?:www.)?youtu((\.be)|(be\..{2,5}))\/((user)|(channel))\/',
    'website': r'^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$',
    'vk': r'^(https?:\/\/)?(?:www.)?(vk\.com|vkontakte\.ru)\/(id\d|[a-zA-Z0-9_.])+$',
    'telegram': r'(?:@|(?:(?:(?:https?://)?t(?:elegram)?)\.me\/))(\w{4,})',
    'instagram': r'(?:(?:http|https):\/\/)?(?:www.)?(?:instagram.com|instagr.am|instagr.com)\/(\w+)',
    'phone_number': r'^\+(?:[0-9] ?){6,14}[0-9]$',
    'name': r'([A-ZÀ-ÿ][-,a-z. \']+[ ]*)+',
}


class AccountAction(str, Enum):
    ACTIVATE = 'activate'
    CHANGE_EMAIL = 'change-email'
    RESET_PASSWORD = 'reset-password'


def check_password_strength(password: str) -> None:
    message = 'Password should contain at least '
    error_log = []
    errors = {
        '1 digit': re.search(r'\d', password) is None,
        '1 uppercase letter': re.search(r'[A-Z]', password) is None,
        '1 lowercase letter': re.search(r'[a-z]', password) is None,
        '1 special character': re.search(r'\W', password) is None,
    }
    for err_msg, error in errors.items():
        if error:
            error_log.append(err_msg)
    if error_log:
        raise ValueError(message + ', '.join(err for err in error_log))


def get_url(
    module_name: str,
    endpoint: str = 'get_one',
    **path_params: Any,
) -> str:
    module = import_module(f'api.v1.{module_name}')
    router: APIRouter = getattr(module, 'router')
    return router.url_path_for(endpoint, **path_params)


def get_image(filename: str, path: str = 'posts') -> Path:
    img_path = config.root_dir / config.upload_dir / path / filename
    if not Path.exists(img_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Image not found',
        )
    return img_path


async def _save_image_to_disk(path: Path, image: memoryview) -> None:
    async with aiofiles.open(path, "wb") as f:
        await f.write(image)


async def save_image(file: UploadFile, *, path: str = 'posts') -> str:
    f_ext = Path(file.filename).suffix if file.filename else '.jpg'
    filename = secrets.token_hex(8) + f_ext
    img_path = config.root_dir / config.upload_dir / path
    img_path.mkdir(parents=True, exist_ok=True)
    img_path = img_path / filename
    detected_content_type = filetype.guess(file.file).extension.lower()

    if file.content_type not in config.accepted_file_types or detected_content_type not in config.accepted_file_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail='Unsupported file type',
        )
    buffer = BytesIO(await file.read())
    size = buffer.getbuffer().nbytes
    if size > config.image_size:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail='Too large')
    if path != 'posts':
        output_size = (150, 150)
        img = Image.open(buffer)
        img.thumbnail(output_size)
        buffer.seek(0)
        buffer.truncate(0)
        img.save(buffer, format='JPEG' if f_ext == '.jpg' else f_ext[1:])
    await _save_image_to_disk(img_path, buffer.getbuffer())
    return filename


def delete_image(filename: str, *, path: str = 'posts') -> None:
    if filename != config.default_avatar:
        img_path = config.root_dir / config.upload_dir / path / filename
        Path.unlink(img_path, missing_ok=True)
