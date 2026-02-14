"""Dependencies FastAPI pour l'authentification."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from dependency_injector.wiring import inject, Provide

from backend.domain.models.user import User
from backend.domain.ports.user_repository_port import UserRepositoryPort
from backend.infrastructure.container import Container
from backend.infrastructure.security import oauth2_scheme, decode_token


@inject
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: UserRepositoryPort = Depends(Provide[Container.user_repository]),
) -> User:
    """
    Dependency FastAPI: extrait l'utilisateur courant du token JWT.

    Supporte deux types de tokens:
    - Token utilisateur: sub=email → lookup en base
    - Token widget: sub="widget" → utilisateur virtuel avec company_id

    Usage dans les routes:
        @router.get("/protected")
        async def protected_route(
            current_user: User = Depends(get_current_user)
        ):
            ...
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = decode_token(token)

    # Token widget (via API key) - pas de lookup user
    if token_data.email == "widget":
        return User(
            user_id="widget",
            email="widget@system",
            hashed_password="",
            company_id=token_data.company_id,
            full_name="Widget User",
            disabled=False,
        )

    # Token utilisateur standard - lookup en base
    user = await user_repo.get_by_email(token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency FastAPI: extrait l'utilisateur courant actif du token JWT.

    Leve une exception si l'utilisateur est desactive.
    """
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return user


# Type alias pour simplifier l'utilisation dans les routes
CurrentUser = Annotated[User, Depends(get_current_active_user)]
