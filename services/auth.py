import smtplib
from datetime import timedelta, datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from core.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_SUBJECT_PASSWORD_RESET, \
    SECRET_KEY, ALGORITHM, SITE_DOMAIN
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext

from .database import get_db
from .user import get_user

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except jwt.JWTError:
        return None
    user = await get_user(username)
    return user


async def authenticate_user(username: str, password: str):
    user = await get_user(username)
    if not user or not verify_password(password, user.password):
        return False
    return user


async def get_user_by_email(email: str):
    user = await get_db().users.find_one({"email": email})
    return user


def create_reset_token(user_id: str):
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {"exp": expire, "sub": user_id}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def send_password_reset_email(email: str, token: str):
    reset_link = f"{SITE_DOMAIN}/reset-password?token={token}"
    message = MIMEMultipart("alternative")
    message["Subject"] = EMAIL_SUBJECT_PASSWORD_RESET
    message["From"] = EMAIL_FROM
    message["To"] = email

    text = f"Please click the link to reset your password: {reset_link}"
    html = f"""\
    <html>
      <body>
        <p>Please click the link to reset your password:<br>
           <a href="{reset_link}">Reset Password</a>
           If you did not request a password reset, please ignore this email.
           If you cannot see the link, please copy and paste the following URL into your browser:<br>
              {reset_link}
        </p>
      </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, email, message.as_string())


def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except jwt.JWTError:
        return None


async def update_user_password(user_id: str, new_password: str):
    hashed_password = get_password_hash(new_password)
    await get_db().users.update_one({"_id": user_id}, {"$set": {"password": hashed_password}})
