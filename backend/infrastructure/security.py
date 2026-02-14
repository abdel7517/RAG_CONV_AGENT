"""
Module de securite pour l'authentification JWT.

Implemente le hachage de mots de passe et la gestion des tokens JWT
selon les recommandations FastAPI:
https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from src.config import settings
from backend.domain.models.user import TokenData, User
from backend.domain.ports.user_repository_port import UserRepositoryPort

# Configuration du hachage de mots de passe (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Schema OAuth2 - le tokenUrl pointe vers l'endpoint de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifie si un mot de passe correspond au hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash un mot de passe avec bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cree un token JWT avec une date d'expiration.

    Args:
        data: Donnees a encoder dans le token (ex: {"sub": email})
        expires_delta: Duree de validite du token

    Returns:
        Token JWT encode
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def authenticate_user(
    user_repo: UserRepositoryPort,
    email: str,
    password: str
) -> Optional[User]:
    """
    Authentifie un utilisateur par email et mot de passe.

    Returns:
        User si authentification reussie, None sinon
    """
    user = await user_repo.get_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def decode_token(token: str) -> TokenData:
    """
    Decode et valide un token JWT.

    Raises:
        HTTPException 401 si le token est invalide
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        company_id: str = payload.get("company_id")
        if email is None:
            raise credentials_exception
        return TokenData(email=email, company_id=company_id)
    except InvalidTokenError:
        raise credentials_exception


class AuthDependency:
    """
    Dependency injectable pour l'authentification.

    Permet d'injecter le repository via le container DI
    tout en fournissant une dependency FastAPI pour les routes.
    """

    def __init__(self, user_repo: UserRepositoryPort):
        self.user_repo = user_repo

    async def get_current_user(
        self,
        token: Annotated[str, Depends(oauth2_scheme)]
    ) -> User:
        """
        Dependency FastAPI: extrait l'utilisateur courant du token JWT.

        Usage dans les routes:
            @router.get("/protected")
            async def protected_route(
                current_user: User = Depends(auth_dependency.get_current_user)
            ):
                ...
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        token_data = decode_token(token)

        user = await self.user_repo.get_by_email(token_data.email)
        if user is None:
            raise credentials_exception
        return user

    async def get_current_active_user(
        self,
        token: Annotated[str, Depends(oauth2_scheme)]
    ) -> User:
        """
        Dependency FastAPI: extrait l'utilisateur courant actif du token JWT.

        Leve une exception si l'utilisateur est desactive.
        """
        user = await self.get_current_user(token)
        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        return user
