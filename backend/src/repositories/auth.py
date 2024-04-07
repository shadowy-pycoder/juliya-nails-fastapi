from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.background import BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from itsdangerous import BadSignature, URLSafeTimedSerializer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import ValidationError

from src.core.config import config
from src.models.users import User
from src.repositories.email import EmailRepository
from src.repositories.socials import SocialRepository
from src.repositories.users import UserRepository
from src.schemas.auth import EmailRequest, ResetRequest, Token, UserPayload, VerifyUserRequest
from src.schemas.socials import SocialCreate
from src.schemas.users import UserAdminUpdatePartial, UserCreate
from src.utils import AccountAction


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/v1/auth/token')


class AuthRepository:
    secret_key = config.SECRET_KEY
    secret_salt = config.SECRET_SALT
    token_expiration = config.CONFIRM_EXPIRATION
    jwt_expiration = config.JWT_EXPIRATION
    jwt_refresh_expiration = config.JWT_REFRESH_EXPIRATION
    jwt_secret_key = config.JWT_SECRET_KEY
    jwt_algorithm = config.JWT_ALGORITHM

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
        exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={'WWW-Authenticate': 'Bearer'},
        )
        if refresh_token:
            exc.detail = 'Invalid refresh token'
        else:
            exc.detail = 'Could not validate credentials'
        try:
            payload = jwt.decode(token, cls.jwt_secret_key, algorithms=[cls.jwt_algorithm])
        except JWTError:
            raise exc from None
        user_data = payload.get('user')
        access: bool = payload.get('access', False)
        if refresh_token and access:
            raise exc from None
        elif not refresh_token and not access:
            exc.detail = 'Invalid access token'
            raise exc from None
        try:
            user = UserPayload.model_validate(user_data)
        except ValidationError:
            raise exc from None
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
        token = self.generate_verification_token(user, context=AccountAction.ACTIVATE)
        await self.email_repo.send_confirmation_email(
            user,
            token,
            background_tasks,
            context=AccountAction.ACTIVATE,
        )
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
            try:
                user = await self.user_repo.find_one(email=form_data.username)
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
                detail='Invalid refresh token',
                headers={'WWW-Authenticate': 'Bearer'},
            ) from None
        access_token = self.create_token(user)
        return Token(access_token=access_token, refresh_token=token), user

    def generate_verification_token(self, instance: User, *, context: AccountAction) -> str | bytes:
        serializer = URLSafeTimedSerializer(self.secret_key)
        salt = self.secret_salt + datetime.strftime(instance.updated, '%Y-%m-%dT%H:%M:%S.%f%z').encode('utf-8')
        return serializer.dumps({context.value: str(instance.email)}, salt=salt)

    def valid_verification_token(
        self,
        instance: User,
        token: str | bytes,
        *,
        context: AccountAction,
    ) -> bool:
        serializer = URLSafeTimedSerializer(self.secret_key)
        salt = self.secret_salt + datetime.strftime(instance.updated, '%Y-%m-%dT%H:%M:%S.%f%z').encode('utf-8')
        try:
            data: dict[str, Any] = serializer.loads(
                token,
                salt=salt,
                max_age=self.token_expiration,
            )
        except BadSignature:
            return False
        except Exception:
            return False
        if data.get(context.value) != str(instance.email):
            return False
        return True

    async def activate_user_account(
        self,
        instance: User,
        data: VerifyUserRequest,
        background_tasks: BackgroundTasks,
        *,
        context: AccountAction,
    ) -> User:
        if instance.confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Account already confirmed.',
            )
        if not self.valid_verification_token(instance, data.token, context=context):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='The confirmation link is invalid or has expired.',
            )
        user_data = UserAdminUpdatePartial(confirmed=True, confirmed_on=datetime.now())
        if context is AccountAction.ACTIVATE:
            user_data.active = True
        user = await self.user_repo.update(instance, user_data, exclude_unset=True)
        if context is AccountAction.ACTIVATE:
            await self.email_repo.send_welcome_email(user, background_tasks)
        return user

    async def resend_confirmation(
        self,
        user: User,
        background_tasks: BackgroundTasks,
        context: AccountAction,
    ) -> None:
        exc = HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
        if user.active and context is AccountAction.ACTIVATE:
            exc.detail = 'Account already activated.'
            raise exc
        if user.confirmed and context is AccountAction.CHANGE_EMAIL:
            exc.detail = 'Account already confirmed.'
            raise exc
        if not user.active and context is AccountAction.CHANGE_EMAIL:
            exc.detail = 'Please activate your account to proceed.'
            raise exc
        token = self.generate_verification_token(user, context=context)
        await self.email_repo.send_confirmation_email(user, token, background_tasks, context=context)

    async def change_email(self, user: User, background_tasks: BackgroundTasks) -> None:
        token = self.generate_verification_token(user, context=AccountAction.CHANGE_EMAIL)
        await self.email_repo.send_confirmation_email(
            user,
            token,
            background_tasks,
            context=AccountAction.CHANGE_EMAIL,
        )

    async def email_forgot_password_link(
        self,
        data: EmailRequest,
        background_tasks: BackgroundTasks,
        *,
        context: AccountAction,
    ) -> None:
        try:
            user = await self.user_repo.find_one(email=data.email)
        except HTTPException:
            return None
        token = self.generate_verification_token(user, context=context)
        await self.email_repo.send_confirmation_email(
            user,
            token,
            background_tasks,
            context=context,
        )

    async def reset_user_password(self, data: ResetRequest) -> None:
        exc = HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
        try:
            user = await self.user_repo.find_one(email=data.email)
        except HTTPException:
            exc.detail = 'The confirmation link is invalid or has expired.'
            raise exc from None
        if not user.confirmed:
            exc.detail = 'Your account is not verified. Please check your email inbox to verify your account.'
            raise exc
        if not user.active:
            exc.detail = 'Your account is inactive. Please activate your account to proceed.'
            raise exc
        if not self.valid_verification_token(
            user,
            data.token,
            context=AccountAction.RESET_PASSWORD,
        ):
            exc.detail = 'The confirmation link is invalid or has expired.'
            raise exc

        user_data = UserAdminUpdatePartial(**data.model_dump())
        await self.user_repo.update(user, user_data, exclude_unset=True)
