from datetime import datetime, timedelta


from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.hash import bcrypt
from pydantic import ValidationError

from models.users import User
from repositories.users import UserRepository
from schemas.auth import UserPayload, Token
from schemas.users import UserCreate
from config import config


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/v1/auth/token')


class AuthRepository:
    def __init__(self, repo: UserRepository = Depends()) -> None:
        self.repo = repo

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
            payload = jwt.decode(token, config.jwt_secret_key, algorithms=[config.jwt_algorithm])
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
            expiration = timedelta(seconds=config.jwt_refresh_expiration)
            access = False
        else:
            expiration = timedelta(seconds=config.jwt_expiration)
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
            config.jwt_secret_key,
            algorithm=config.jwt_algorithm,
        )
        return token

    async def register_user(self, user_data: UserCreate) -> User:
        return await self.repo.create(user_data)

    async def get_token(self, form_data: OAuth2PasswordRequestForm) -> tuple[Token, User]:
        exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
        try:
            user = await self.repo.find_one(username=form_data.username)
        except HTTPException:
            raise exception from None
        if not self.verify_password(form_data.password, user.hashed_password):
            raise exception from None
        access_token = self.create_token(user)
        refresh_token = self.create_token(user, refresh_token=True)
        return Token(access_token=access_token, refresh_token=refresh_token), user

    async def get_refresh_token(self, token: str) -> tuple[Token, User]:
        user_payload = AuthRepository.validate_token(token, refresh_token=True)
        try:
            user = await self.repo.find_by_uuid(user_payload.uuid)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        access_token = self.create_token(user)
        return Token(access_token=access_token, refresh_token=token), user
