from io import BytesIO
from pathlib import Path
import secrets

import aiofiles
from PIL import Image
from fastapi import UploadFile

from config import config

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


async def _save_image_to_disk(path: Path, image: memoryview) -> None:
    async with aiofiles.open(path, "wb") as f:
        await f.write(image)


async def save_image(file: UploadFile, path: str = 'posts') -> str:
    f_ext = Path(file.filename).suffix if file.filename else '.jpg'
    filename = secrets.token_hex(8) + f_ext
    img_path = config.root_dir / config.upload_dir / path
    img_path.mkdir(parents=True, exist_ok=True)
    img_path = img_path / filename
    buffer = BytesIO(await file.read())
    if path != 'posts':
        output_size = (150, 150)
        img = Image.open(buffer)
        img.thumbnail(output_size)
        buffer.seek(0)
        buffer.truncate(0)
        img.save(buffer, format='JPEG' if f_ext == '.jpg' else f_ext[1:])
    await _save_image_to_disk(img_path, buffer.getbuffer())
    return filename


def delete_image(filename: str, path: str = 'posts') -> None:
    if filename != config.default_avatar:
        img_path = config.root_dir / config.upload_dir / path / filename
        Path.unlink(img_path, missing_ok=True)
