from datetime import datetime, timedelta


from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.hash import bcrypt
from pydantic import ValidationError

from models.users import User
from services.users import UserService
from settings import settings
from schemas.auth import UserPayload, Token
from schemas.users import UserRead, UserCreate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/v1/auth/token')


async def get_current_user(token: str = Depends(oauth2_scheme), service: UserService = Depends()) -> UserRead:
    user_payload = AuthService.validate_token(token)
    return UserRead.model_validate(await service.find_by_uuid(user_payload.uuid))


class AuthService:
    def __init__(self, service: UserService = Depends()) -> None:
        self.service = service

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.verify(plain_password, hashed_password)

    @classmethod
    def validate_token(cls, token: str, refresh_token: bool = False) -> UserPayload:
        if refresh_token:
            exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate credentials',
                headers={'WWW-Authenticate': 'Bearer'},
            )
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        except JWTError:
            raise exception from None
        user_data = payload.get('user')
        access: bool = payload.get('access', False)
        if refresh_token and access:
            raise exception from None
        elif not refresh_token and not access:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        try:
            user = UserPayload.model_validate(user_data)
        except ValidationError:
            raise exception from None
        return user

    @classmethod
    def create_token(cls, user: User, refresh_token: bool = False) -> str:
        user_data = UserPayload.model_validate(user)
        now = datetime.utcnow()
        if refresh_token:
            expiration = timedelta(seconds=settings.jwt_refresh_expiration)
            access = False
        else:
            expiration = timedelta(seconds=settings.jwt_expiration)
            access = True
        payload = {
            'iat': now,
            'nbf': now,
            'exp': now + expiration,
            'sub': user_data.uuid,
            'user': user_data.model_dump(),
            'access': access,
        }
        token = jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        return token

    async def register_user(self, user_data: UserCreate) -> UserRead:
        user = await self.service.create(user_data)
        return UserRead.model_validate(user)

    async def get_token(self, form_data: OAuth2PasswordRequestForm) -> tuple[Token, User]:
        exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
        user = await self.service.find_one_or_none(username=form_data.username)
        if not user:
            raise exception
        if not self.verify_password(form_data.password, user.hashed_password):
            raise exception
        access_token = self.create_token(user)
        refresh_token = self.create_token(user, refresh_token=True)
        return Token(access_token=access_token, refresh_token=refresh_token), user

    async def get_refresh_token(self, token: str) -> tuple[Token, User]:
        user_payload = AuthService.validate_token(token, refresh_token=True)
        user: User | None = await self.service.find_by_uuid(user_payload.uuid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = self.create_token(user)
        return Token(access_token=access_token, refresh_token=token), user
