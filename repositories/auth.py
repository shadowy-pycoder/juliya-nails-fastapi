from datetime import datetime, timedelta
from typing import Any


from fastapi import HTTPException, status, Depends
from fastapi.background import BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from itsdangerous import URLSafeTimedSerializer, BadSignature
from jose import jwt, JWTError
from passlib.hash import bcrypt
from pydantic import ValidationError

from config import config
from models.users import User
from repositories.email import EmailRepository
from repositories.socials import SocialRepository
from repositories.users import UserRepository
from schemas.auth import UserPayload, Token, VerifyUserRequest
from schemas.socials import SocialCreate
from schemas.users import UserCreate, UserAdminUpdatePartial


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/v1/auth/token')


class AuthRepository:
    secret_key = config.secret_key
    secret_salt = config.secret_salt
    token_expiration = config.confirm_expiration
    jwt_expiration = config.jwt_expiration
    jwt_refresh_expiration = config.jwt_refresh_expiration
    jwt_secret_key = config.jwt_secret_key
    jwt_algorithm = config.jwt_algorithm

    def __init__(
        self,
        user_repo: UserRepository = Depends(),
        email_repo: EmailRepository = Depends(),
        social_repo: SocialRepository = Depends(),
    ) -> None:
        self.user_repo = user_repo
        self.email_repo = email_repo
        self.social_repo = social_repo

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
            payload = jwt.decode(token, cls.jwt_secret_key, algorithms=[cls.jwt_algorithm])
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
            expiration = timedelta(seconds=cls.jwt_refresh_expiration)
            access = False
        else:
            expiration = timedelta(seconds=cls.jwt_expiration)
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
            cls.jwt_secret_key,
            algorithm=cls.jwt_algorithm,
        )
        return token

    async def register_user(self, user_data: UserCreate, background_tasks: BackgroundTasks) -> User:
        user = await self.user_repo.create(user_data)
        await self.social_repo.create(SocialCreate(user_id=user.uuid))
        token = self.generate_verification_token(user)
        await self.email_repo.send_confirmation_email(user, token, background_tasks)
        return user

    async def get_token(self, form_data: OAuth2PasswordRequestForm) -> tuple[Token, User]:
        exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
        try:
            user = await self.user_repo.find_one(username=form_data.username)
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
            user = await self.user_repo.find_by_uuid(user_payload.uuid)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        access_token = self.create_token(user)
        return Token(access_token=access_token, refresh_token=token), user

    def generate_verification_token(self, instance: User, context: str = 'confirm') -> str | bytes:
        serializer = URLSafeTimedSerializer(self.secret_key)
        return serializer.dumps({context: str(instance.uuid)}, salt=self.secret_salt)

    def valid_verification_token(
        self,
        instance: User,
        token: str | bytes,
        context: str = 'confirm',
    ) -> bool:
        serializer = URLSafeTimedSerializer(self.secret_key)
        try:
            data: dict[str, Any] = serializer.loads(
                token,
                salt=self.secret_salt,
                max_age=self.token_expiration,
            )
        except BadSignature:
            return False
        except Exception:
            return False
        if data.get(context) != str(instance.uuid):
            return False
        return True

    async def activate_user_account(
        self,
        instance: User,
        data: VerifyUserRequest,
        background_tasks: BackgroundTasks,
    ) -> User:
        if instance.confirmed:
            raise HTTPException(status_code=400, detail='Account already confirmed.')
        if not self.valid_verification_token(instance, data.token):
            raise HTTPException(status_code=400, detail='The confirmation link is invalid or has expired.')
        user_data = UserAdminUpdatePartial(confirmed=True, confirmed_on=datetime.utcnow())
        user = await self.user_repo.update(instance, user_data, exclude_unset=True)
        await self.email_repo.send_welcome_email(user, background_tasks)
        return user
