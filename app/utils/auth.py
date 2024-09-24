from datetime import datetime, timedelta
from typing import Optional, Union
from fastapi import Form, HTTPException, Request, status
from fastapi.security import OAuth2
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.openapi.models import OAuthFlows
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.orm import Session

from ..models import User
from ..core.config import get_settings

pwd_hash = PasswordHash(
    [
        BcryptHasher(),
    ]
)


def get_password_hash(password):
    """
    Returns a hashed version of the provided password.

    Args:
        password (str): The password to be hashed.

    Returns:
        str: The hashed password.
    """
    return pwd_hash.hash(password)


def verify_password(plain_password, hashed_password):
    """
    Verifies a plain password against a hashed password.

    Args:
        plain_password (str): The password to be verified.
        hashed_password (str): The hashed password to verify against.

    Returns:
        bool: True if the plain password matches the hashed password, False otherwise.
    """
    return pwd_hash.verify(plain_password, hashed_password)


def authenticate_user(db: Session, username: str, password: str):
    if not username or not password:
        return False

    # Retrieve the user from the database
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    if not user.is_active:
        return False
    return user


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    """
    Creates an access token for the given data.

    Args:
        data (dict): The data to be encoded in the token.
        expires_delta (Union[timedelta, None], optional): The duration the token will expire after.
            If not provided, the token will expire after the duration specified in the settings.

    Returns:
        str: The encoded token data.
    """
    # Copy the data to avoid modifying the original dictionary
    to_encode = data.copy()

    # Retrieve the settings
    settings = get_settings()

    # Calculate the expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    # Add the expiration time to the data
    to_encode.update({"exp": expire})

    # Return the encoded token data
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key.get_secret_value(), algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str):
    settings = get_settings()

    return jwt.decode(
        token, settings.secret_key.get_secret_value(), algorithms=[settings.algorithm]
    )


class OAuth2ClientCredentials(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: str = None,
        scopes: dict = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlows(clientCredentials={"scopes": scopes, "tokenUrl": tokenUrl})
        super().__init__(
            flows=flows,
            scheme_name=scheme_name,
            auto_error=auto_error,
        )

    def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param


class OAuth2ClientCredentialsRequestForm:
    """
    This is dependency class to collect the client credentials from
    the request form data for OAuth2 client credentials flow.

    Attributes:
        grant_type (str): The grant type of the request. In this case, it must
            be "client_credentials".
        scope (str): The scope of the request. This is a space-delimited list of
            scope values.
        client_id (str, optional): The client ID of the client making the
            request.
        client_secret (str, optional): The client secret of the client making
            the request.
    """

    def __init__(
        self,
        grant_type: str = Form(None, pattern="client_credentials"),
        scope: str = Form(""),
        client_id: Optional[str] = Form(None),
        client_secret: Optional[str] = Form(None),
    ):
        """
        Initialize the OAuth2 client credentials request form.

        Args:
            grant_type (str): The grant type of the request. In this case, it must
                be "client_credentials".
            scope (str): The scope of the request. This is a space-delimited list of
                scope values.
            client_id (str, optional): The client ID of the client making the
                request.
            client_secret (str, optional): The client secret of the client making
                the request.
        """
        self.grant_type = grant_type
        self.scope = scope.split()
        self.client_id = client_id
        self.client_secret = client_secret
