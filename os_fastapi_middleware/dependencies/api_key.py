from typing import Optional
from fastapi import Header, Depends, HTTPException, status

from os_fastapi_middleware.providers.base import BaseAPIKeyProvider
from os_fastapi_middleware.exceptions import UnauthorizedException, ForbiddenException


class APIKeyDependency:
    
    def __init__(
        self,
        provider: BaseAPIKeyProvider,
        header_name: str = "X-API-Key",
        auto_error: bool = True
    ):
        self.provider = provider
        self.header_name = header_name
        self.auto_error = auto_error
    
    async def __call__(self, api_key: Optional[str] = Header(None, alias="X-API-Key")):
        if not api_key:
            if self.auto_error:
                raise UnauthorizedException(f"API key required in '{self.header_name}' header")
            return None
        
        is_valid = await self.provider.validate_key(api_key)
        
        if not is_valid:
            if self.auto_error:
                raise ForbiddenException("Invalid API key")
            return None
        
        return api_key


def get_api_key_metadata(provider: BaseAPIKeyProvider):
    
    async def dependency(api_key: str = Depends(APIKeyDependency(provider))):
        metadata = await provider.get_key_metadata(api_key)
        return metadata
    
    return dependency