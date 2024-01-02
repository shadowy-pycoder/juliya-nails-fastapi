from fastapi import APIRouter
from .v1.auth import router as auth_router_v1
from .v1.posts import router as posts_router_v1
from .v1.socials import router as socials_router_v1
from .v1.users import router as users_router_v1


router_v1 = APIRouter()
router_v1.include_router(auth_router_v1)
router_v1.include_router(posts_router_v1)
router_v1.include_router(socials_router_v1)
router_v1.include_router(users_router_v1)
