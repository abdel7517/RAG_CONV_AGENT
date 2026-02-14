"""Routes d'authentification JWT."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from dependency_injector.wiring import inject, Provide

from src.config import settings
from backend.domain.models.user import Token, User, UserCreate, UserResponse
from backend.domain.ports.user_repository_port import UserRepositoryPort
from backend.domain.ports.company_repository_port import CompanyRepositoryPort
from backend.infrastructure.container import Container
from backend.infrastructure.security import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    oauth2_scheme,
    decode_token,
)

router = APIRouter()


@router.post("/token", response_model=Token)
@inject
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repo: UserRepositoryPort = Depends(Provide[Container.user_repository]),
) -> Token:
    """
    OAuth2 compatible token login.

    Authentifie l'utilisateur et retourne un token JWT.
    Le username correspond a l'email de l'utilisateur.
    """
    user = await authenticate_user(user_repo, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "company_id": user.company_id},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@inject
async def register_user(
    user_data: UserCreate,
    user_repo: UserRepositoryPort = Depends(Provide[Container.user_repository]),
) -> UserResponse:
    """
    Enregistre un nouvel utilisateur.

    L'email doit etre unique. Le mot de passe est hashe avec bcrypt.
    """
    # Verifier si l'email existe deja
    if await user_repo.email_exists(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Creer l'utilisateur avec le mot de passe hashe
    user = User.create(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        company_id=user_data.company_id,
        full_name=user_data.full_name,
    )

    await user_repo.create(user)

    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        company_id=user.company_id,
        full_name=user.full_name,
        disabled=user.disabled,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.get("/me", response_model=UserResponse)
@inject
async def read_users_me(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: UserRepositoryPort = Depends(Provide[Container.user_repository]),
) -> UserResponse:
    """
    Retourne les informations de l'utilisateur connecte.

    Necessite un token JWT valide dans le header Authorization.
    """
    token_data = decode_token(token)

    user = await user_repo.get_by_email(token_data.email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        company_id=user.company_id,
        full_name=user.full_name,
        disabled=user.disabled,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.get("/token", response_model=Token)
@inject
async def get_token_from_api_key(
    api_key: str = Header(..., alias="X-API-Key"),
    company_repo: CompanyRepositoryPort = Depends(Provide[Container.company_repository]),
) -> Token:
    """
    Obtient un JWT via l'API key de l'entreprise.

    Utilise par les sites partenaires pour authentifier leur widget chatbot.
    Le token retourne a une validite de 24 heures.

    Header requis: X-API-Key
    """
    company = await company_repo.get_by_api_key(api_key)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": "widget", "company_id": company.company_id},
        expires_delta=timedelta(hours=24),
    )
    return Token(access_token=access_token, token_type="bearer")
