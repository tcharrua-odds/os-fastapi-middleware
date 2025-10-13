from typing import Optional, Callable, List
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import status

from os_fastapi_middleware.providers.base import BaseAPIKeyProvider


class APIKeyMiddleware(BaseHTTPMiddleware):
    
    def __init__(
        self,
        app,
        provider: BaseAPIKeyProvider,
        header_name: str = "X-API-Key",
        exempt_paths: Optional[List[str]] = None,
        on_error: Optional[Callable] = None,
        include_metadata: bool = False
    ):
        """
        Args:
            app: Application FastAPI/Starlette
            provider: Provider to validate API keys
            header_name: Header name to get an API key from
            exempt_paths: Path list to exempt from authentication
            on_error: Customized callback for error responses
            include_metadata: If true, include metadata in request state
        """
        super().__init__(app)
        self.provider = provider
        self.header_name = header_name
        self.exempt_paths = exempt_paths or []
        self.on_error = on_error
        self.include_metadata = include_metadata
    
    async def dispatch(self, request: Request, call_next):
        # Check if the path is exempt from authentication
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        api_key = request.headers.get(self.header_name)
        
        if not api_key:
            return self._error_response(
                status.HTTP_401_UNAUTHORIZED,
                f"API key required in '{self.header_name}' header"
            )

        try:
            is_valid = await self.provider.validate_key(api_key)
            
            if not is_valid:
                return self._error_response(
                    status.HTTP_403_FORBIDDEN,
                    "Invalid API key"
                )

            if self.include_metadata:
                metadata = await self.provider.get_key_metadata(api_key)
                request.state.api_key_metadata = metadata

            request.state.api_key = api_key
            
            return await call_next(request)
            
        except Exception as e:
            if self.on_error:
                return self.on_error(request, e)
            
            return self._error_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Error validating API key"
            )
    
    @staticmethod
    def _error_response(status_code: int, detail: str):
        return JSONResponse(
            status_code=status_code,
            content={"detail": detail}
        )