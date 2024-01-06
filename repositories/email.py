from typing import Any

from fastapi.background import BackgroundTasks
from fastapi_mail import MessageSchema, MessageType

from config import fm, config
from models.users import User
from utils import AccountAction


class EmailRepository:
    async def send_email(
        self,
        recipients: list[str],
        subject: str,
        context: dict[str, Any],
        template_name: str,
        background_tasks: BackgroundTasks,
    ) -> None:
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=context,
            subtype=MessageType.html,
        )
        background_tasks.add_task(fm.send_message, message, template_name=template_name)

    async def send_confirmation_email(
        self,
        user: User,
        token: str | bytes,
        background_tasks: BackgroundTasks,
        *,
        context: AccountAction,
    ) -> None:
        if context is AccountAction.ACTIVATE:
            subject = f'Account Activation - {config.app_name}'
            action = 'activate account'
        else:
            subject = f'Email Change - {config.app_name}'
            action = 'change email'
        activate_url = f'{config.frontend_host}/auth/confirm/{str(token)}'
        data = {
            'app_name': config.app_name,
            'username': user.username,
            'activate_url': activate_url,
            'action': action,
        }
        await self.send_email(
            recipients=[user.email],
            subject=subject,
            template_name='confirm_email.html',
            context=data,
            background_tasks=background_tasks,
        )

    async def send_welcome_email(
        self,
        user: User,
        background_tasks: BackgroundTasks,
    ) -> None:
        data = {'app_name': config.app_name, 'username': user.username, 'login_url': f'{config.frontend_host}'}
        subject = f'Welcome - {config.app_name}'
        await self.send_email(
            recipients=[user.email],
            subject=subject,
            template_name='welcome.html',
            context=data,
            background_tasks=background_tasks,
        )
