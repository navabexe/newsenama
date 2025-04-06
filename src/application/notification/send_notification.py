# File: src/application/notification/send_notification.py

from fastapi import APIRouter, Request, status, Depends
from pydantic import Field
from typing import Annotated, Literal, Optional
from redis.asyncio import Redis

from common.security.jwt_handler import get_current_user
from domain.notification.entities.notification_entity import NotificationChannel
from domain.notification.notification_services.notification_service import notification_service
from common.schemas.request_base import BaseRequestModel
from common.schemas.standard_response import StandardResponse, Meta
from common.translations.messages import get_message
from common.logging.logger import log_info, log_error
from common.exceptions.base_exception import BadRequestException, InternalServerErrorException
from common.utils.ip_utils import extract_client_ip
from infrastructure.database.redis.redis_client import get_redis_client

router = APIRouter()

class SendNotificationRequest(BaseRequestModel):
    receiver_id: Annotated[str, Field(min_length=1, description="ID of the recipient (user/vendor/admin)")]
    receiver_type: Annotated[Literal["user", "vendor", "admin"], Field(description="Type of recipient")]
    template_key: Annotated[str, Field(min_length=1, description="Template key for notification content")]
    channel: Annotated[NotificationChannel, Field(default=NotificationChannel.INAPP, description="Notification delivery channel")]
    reference_type: Annotated[Optional[str], Field(default=None, description="Type of related entity (e.g., 'otp', 'order')")]
    reference_id: Annotated[Optional[str], Field(default=None, description="ID of related entity")]
    variables: Annotated[Optional[dict], Field(default=None, description="Variables to inject into the template")]
    device_fingerprint: Annotated[Optional[str], Field(default=None, description="Device fingerprint for tracking")]

    model_config = {
        "str_strip_whitespace": True,
        "extra": "forbid"
    }

@router.post(
    "/send-notification",
    status_code=status.HTTP_200_OK,
    response_model=StandardResponse,
    summary="Send a notification",
    description="Send a notification to a recipient via the chosen channel (currently only INAPP supported). Requires JWT access token.",
    tags=["Notifications"]
)
async def send_notification_endpoint(
    data: SendNotificationRequest,
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)],
    current_user: Annotated[dict, Depends(get_current_user)]
):
    client_ip = extract_client_ip(request)
    language = data.response_language
    created_by = current_user["user_id"]

    # Rate limiting
    rate_limit_key = f"notification_limit:{data.receiver_id}:{created_by}"
    attempts = await redis.get(rate_limit_key)
    if attempts and int(attempts) >= 10:
        raise BadRequestException(detail=get_message("notification.too_many", lang=language))
    await redis.incr(rate_limit_key)
    await redis.expire(rate_limit_key, 3600)

    try:
        notification_id = await notification_service.send(
            receiver_id=data.receiver_id,
            receiver_type=data.receiver_type,
            template_key=data.template_key,
            channel=data.channel,
            variables=data.variables,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            created_by=created_by,
            language=language
        )

        log_info("Notification sent", extra={
            "notification_id": notification_id,
            "receiver_id": data.receiver_id,
            "receiver_type": data.receiver_type,
            "template_key": data.template_key,
            "channel": data.channel.value,
            "ip": client_ip,
            "created_by": created_by,
            "endpoint": "/send-notification",
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        })

        return StandardResponse(
            meta=Meta(
                message=get_message("notification.sent", lang=language),
                status="success",
                code=200
            ),
            data={
                "notification_id": notification_id,
                "channel": data.channel.value
            }
        )

    except ValueError as e:
        log_error("Invalid notification request", extra={
            "error": str(e),
            "receiver_id": data.receiver_id,
            "template_key": data.template_key,
            "ip": client_ip,
            "endpoint": "/send-notification",
            "request_id": data.request_id
        })
        raise BadRequestException(detail=str(e))

    except Exception as e:
        log_error("Failed to send notification", extra={
            "error": str(e),
            "receiver_id": data.receiver_id,
            "template_key": data.template_key,
            "ip": client_ip,
            "endpoint": "/send-notification",
            "request_id": data.request_id,
            "client_version": data.client_version,
            "device_fingerprint": data.device_fingerprint
        }, exc_info=True)
        raise InternalServerErrorException(detail=get_message("server.error", lang=language))