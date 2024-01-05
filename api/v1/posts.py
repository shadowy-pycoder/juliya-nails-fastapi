from typing import Annotated

from fastapi import APIRouter, Response, status, Depends, Form, UploadFile, File
from fastapi_cache.decorator import cache
from fastapi_filter import FilterDepends
from fastapi_pagination.links import Page
from fastapi.responses import FileResponse
from pydantic import UUID4

from api.v1.dependencies import get_current_user, get_admin_user, get_active_user
from models.users import User
from repositories.posts import PostRepository
from schemas.posts import PostRead, PostCreate, PostFilter, PostAdminUpdate, PostAdminUpdatePartial


router = APIRouter(
    prefix='/api/v1/posts',
    tags=['posts'],
    dependencies=[Depends(get_current_user), Depends(get_active_user)],
    responses={404: {'description': 'Not found'}, 401: {'description': 'Unauthorized'}},
)


@router.post(
    '/',
    status_code=status.HTTP_201_CREATED,
    response_model=PostRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        413: {'description': 'Too large'},
        415: {'description': 'Unsupported file type'},
        403: {'description': 'You are not allowed to perform this operation'},
    },
)
async def create_one(
    response: Response,
    title: Annotated[str, Form(min_length=2, max_length=100)],
    image: UploadFile,
    content: Annotated[str, Form(min_length=2)],
    user: User = Depends(get_current_user),
    repo: PostRepository = Depends(),
) -> PostRead:
    filename = await repo.save_post_image(image)
    post_schema = PostCreate(author_id=user.uuid, title=title, image=filename, content=content)
    post = await repo.create(post_schema)
    response.headers['Location'] = router.url_path_for('get_one', uuid=post.uuid)
    return PostRead.model_validate(post)


@router.get('/', response_model=Page[PostRead])
@cache()
async def get_all(post_filter: PostFilter = FilterDepends(PostFilter), repo: PostRepository = Depends()) -> Page[PostRead]:
    return await repo.find_all(post_filter)


@router.get('/{uuid}', response_model=PostRead)
@cache()
async def get_one(uuid: UUID4 | str, repo: PostRepository = Depends()) -> PostRead:
    post = await repo.find_by_uuid(uuid, detail='Post does not exist')
    return PostRead.model_validate(post)


@router.get('/{uuid}/image', response_class=FileResponse)
async def get_post_image(uuid: UUID4 | str, repo: PostRepository = Depends()) -> FileResponse:
    post = await repo.find_by_uuid(uuid, detail='Post does not exist')
    return FileResponse(repo.get_post_image(post))


@router.put(
    '/{uuid}',
    response_model=PostRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        413: {'description': 'Too large'},
        415: {'description': 'Unsupported file type'},
        403: {'description': 'You are not allowed to perform this operation'},
    },
)
async def update_one(
    uuid: UUID4 | str,
    title: Annotated[str, Form(min_length=2, max_length=100)],
    image: UploadFile,
    content: Annotated[str, Form(min_length=2)],
    repo: PostRepository = Depends(),
) -> PostRead:
    post = await repo.find_by_uuid(uuid, detail='Post does not exist')
    filename = await repo.save_post_image(image)
    post_schema = PostAdminUpdate(title=title, image=filename, content=content)
    post = await repo.update(post, post_schema)
    return PostRead.model_validate(post)


@router.patch(
    '/{uuid}',
    response_model=PostRead,
    dependencies=[Depends(get_admin_user)],
    responses={
        413: {'description': 'Too large'},
        415: {'description': 'Unsupported file type'},
        403: {'description': 'You are not allowed to perform this operation'},
    },
)
async def patch_one(
    uuid: UUID4 | str,
    title: Annotated[str | None, Form(min_length=2, max_length=100)] = None,
    image: UploadFile = File(None),
    content: Annotated[str | None, Form(min_length=2)] = None,
    repo: PostRepository = Depends(),
) -> PostRead:
    post = await repo.find_by_uuid(uuid, detail='Post does not exist')
    filename = await repo.save_post_image(image) if image else None
    post_schema = PostAdminUpdatePartial(title=title, image=filename, content=content)
    post = await repo.update(post, post_schema, exclude_none=True)
    return PostRead.model_validate(post)


@router.delete(
    '/{uuid}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_admin_user)],
    responses={403: {'description': 'You are not allowed to perform this operation'}},
)
async def delete_one(uuid: UUID4 | str, repo: PostRepository = Depends()) -> None:
    post = await repo.find_by_uuid(uuid, detail='Post does not exist')
    await repo.delete(post)
