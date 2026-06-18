from fastapi import APIRouter, Depends, HTTPException
from src.db.connection import get_login_db
from src.config.security import hash_password, verify_password, create_access_token
from sqlalchemy import select
from src.models.schemas import LoginRequest
from sqlalchemy.ext.asyncio import AsyncSession 
import src.service.auth_service as auth_service
from src.utils.logger import get_logger
from src.models.db_models import User
import http
from src.models.schemas import HTTPResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger= get_logger(__name__)

@router.post("/login", response_model=HTTPResponse)
async def login(
    credentials: LoginRequest, db: AsyncSession = Depends(get_login_db)
):
    try:      
        user:User= await auth_service.get_user_by_email(db, credentials.email)
        if user:
            user=user.__dict__
            logger.debug(f"Verifying password for user: {credentials.email}")
            if not verify_password(credentials.password, user["hashed_password"]):
                return HTTPResponse(
                    data=None,
                    message="Invalid email or password",
                    status=http.HTTPStatus.UNAUTHORIZED
                )

            token = create_access_token(
                tenant_id=str(user["tenant_id"]),
                user_id=str(user["id"]),
                role=user["role"],
            )
            return HTTPResponse(
                data={"access_token": token},
                message="Login successful",
                status=http.HTTPStatus.OK
            )
        else: # create user on the fly if it doesn't exist.
            tenant= credentials.email.split("@")[1]
            logger.debug(f"Creating new user for tenant: {tenant} and email: {credentials.email}")
            new_user = await auth_service.create_user(
                db, email=credentials.email, hashed_password=hash_password(credentials.password), tenant=tenant
            )
            token = create_access_token(
                tenant_id=str(new_user.tenant_id),
                user_id=str(new_user.id),
                role=new_user.role,
            )
            logger.info(f"User created and logged in successfully: {credentials.email}")
            return HTTPResponse(
                data={"access_token": token},
                message="User created and logged in successfully",
                status=http.HTTPStatus.CREATED
            )
    except Exception as e:
        logger.error(f"Login error: {e}")
        return  HTTPResponse(
            data=None,
            message="Login failed",
            status=http.HTTPStatus.INTERNAL_SERVER_ERROR
        )
       




