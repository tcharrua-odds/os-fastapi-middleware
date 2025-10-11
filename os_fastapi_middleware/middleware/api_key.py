from typing import Optional, Callable, List
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import status

from os_fastapi_middleware.providers.base import BaseAPIKeyProvider


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware para autenticação via API key.
    Totalmente adaptável através de providers customizados.
    """
    
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
            app: Aplicação FastAPI/Starlette
            provider: Provider para validação de API keys
            header_name: Nome do header onde a API key é enviada
            exempt_paths: Lista de paths que não requerem autenticação
            on_error: Callback customizado para erros
            include_metadata: Se True, adiciona metadados da key ao request.state
        """
        super().__init__(app)
        self.provider = provider
        self.header_name = header_name
        self.exempt_paths = exempt_paths or [
            "/health", "/health/", 
            "/docs", "/redoc", "/openapi.json"
        ]
        self.on_error = on_error
        self.include_metadata = include_metadata
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get(self.header_name)
        
        if not api_key:
            return self._error_response(
                status.HTTP_401_UNAUTHORIZED,
                f"API key required in '{self.header_name}' header"
            )
        
        # Validate API key using provider
        try:
            is_valid = await self.provider.validate_key(api_key)
            
            if not is_valid:
                return self._error_response(
                    status.HTTP_403_FORBIDDEN,
                    "Invalid API key"
                )
            
            # Optionally include metadata in request state
            if self.include_metadata:
                metadata = await self.provider.get_key_metadata(api_key)
                request.state.api_key_metadata = metadata
            
            # Store API key in request state for downstream usage
            request.state.api_key = api_key
            
            return await call_next(request)
            
        except Exception as e:
            if self.on_error:
                return self.on_error(request, e)
            
            return self._error_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Error validating API key"
            )
    
    def _error_response(self, status_code: int, detail: str):
        """Helper para criar respostas de erro consistentes."""
        return JSONResponse(
            status_code=status_code,
            content={"detail": detail}
        )