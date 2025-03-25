from fastapi import APIRouter, Request, Depends, HTTPException, status
from common.security.jwt_handler import get_current_user
from domain.auth.auth_services.auth_service.logout import logout_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Log out from the current session.

    Args:
        request (Request): FastAPI request object.
        current_user (dict): Current user data from JWT token.

    Returns:
        dict: Logout confirmation message.
    """
    try:
        return await logout_service(current_user["user_id"], current_user["session_id"], request.client.host)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to logout")