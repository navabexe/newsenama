# File: src/common/dependencies/ip_dep.py
from fastapi import Request, Depends
from common.utils.ip_utils import extract_client_ip

async def get_client_ip(request: Request) -> str:
    return await extract_client_ip(request)