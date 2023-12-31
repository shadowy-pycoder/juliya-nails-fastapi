from models.socials import SocialMedia
from services.base import BaseService
from schemas.socials import (
    SocialRead,
    SocialCreate,
    SocialUpdate,
    SocialUpdatePartial,
    SocialAdminUpdate,
    SocialAdminUpdatePartial,
    SocialFilter,
)


class SocialService(
    BaseService[
        SocialMedia,
        SocialRead,
        SocialCreate,
        SocialUpdate,
        SocialUpdatePartial,
        SocialAdminUpdate,
        SocialAdminUpdatePartial,
        SocialFilter,
    ]
):
    model = SocialMedia
    schema = SocialRead
    filter_type = SocialFilter
