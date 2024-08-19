from datetime import datetime, timedelta
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy.orm import Session
from typing import Union

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
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt
