from typing import Optional, List, Callable, Union, Dict, Any
from datetime import datetime, timezone

from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware

from os_fastapi_middleware.providers.base import BaseRequestLogProvider


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests/responses through a pluggable provider.

    Usage example:
        provider = MyElasticProvider(...)  # implements BaseRequestLogProvider
        app.add_middleware(RequestLoggingMiddleware, provider=provider)

    By default, it will not log bodies to avoid consuming the body stream.
    """

    def __init__(
        self,
        app,
        provider: Union[BaseRequestLogProvider, Callable[[Dict[str, Any]], Any]],
        exempt_paths: Optional[List[str]] = None,
        include_headers: bool = True,
        capture_body: bool = False,
        max_body_bytes: int = 2048,
        extra_fields: Optional[Dict[str, Any]] = None,
        on_error: Optional[Callable[[Exception], Any]] = None,
    ) -> None:
        """
        Args:
            app: FastAPI/Starlette app
            provider: A BaseRequestLogProvider instance or a callable(record) → None/awaitable
            exempt_paths: List of paths to skip logging
            include_headers: If true, include a small, safe subset of headers
            capture_body: If true, capture small request body (may impact performance)
            max_body_bytes: Max bytes of body to capture when capture_body=True
            extra_fields: Dict with extra static fields added to every record
            on_error: Optional callback if logging raises an exception
        """
        super().__init__(app)
        self._provider = provider
        self._exempt_paths = set(exempt_paths or [
            "/health", "/health/", "/docs", "/redoc", "/openapi.json"
        ])
        self._include_headers = include_headers
        self._capture_body = capture_body
        self._max_body_bytes = max_body_bytes
        self._extra_fields = extra_fields or {}
        self._on_error = on_error

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._exempt_paths:
            return await call_next(request)

        started = datetime.now(timezone.utc)
        request_id = getattr(request.state, "request_id", None)

        # Basic request data
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        referer = request.headers.get("referer")
        host = request.headers.get("host")
        forwarded_for = request.headers.get("x-forwarded-for")
        real_ip = request.headers.get("x-real-ip")

        # Optionally capture a small request body (best-effort, non-intrusive)
        request_body_snippet = None
        content_length = self._safe_int(request.headers.get("content-length"))
        if self._capture_body:
            try:
                # Reading body here is generally okay with BaseHTTPMiddleware since we won't re-use it.
                body = await request.body()
                if body:
                    request_body_snippet = body[: self._max_body_bytes].decode(
                        errors="replace"
                    )
            except Exception:
                request_body_snippet = None

        try:
            response = await call_next(request)
        except Exception as e:
            # Even if the handler fails, we still want to record the attempt
            ended = datetime.now(timezone.utc)
            duration_ms = int((ended - started).total_seconds() * 1000)
            record = {
                "timestamp": started.isoformat(),
                "method": request.method,
                "path": request.url.path,
                "query": request.url.query,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_id": request_id,
                "status_code": 500,
                "duration_ms": duration_ms,
                "content_length": content_length,
                "response_length": None,
                "headers": {
                    "referer": referer,
                    "host": host,
                    "forwarded_for": forwarded_for,
                    "real_ip": real_ip,
                } if self._include_headers else None,
                "request_body": request_body_snippet if self._capture_body else None,
            }
            if self._extra_fields:
                record.update(self._extra_fields)
            await self._emit(record)
            raise

        # Normal flow
        ended = datetime.now(timezone.utc)
        duration_ms = int((ended - started).total_seconds() * 1000)
        response_length = self._safe_int(response.headers.get("content-length"))

        record = {
            "timestamp": started.isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "request_id": request_id,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "content_length": content_length,
            "response_length": response_length,
            "headers": {
                "referer": referer,
                "host": host,
                "forwarded_for": forwarded_for,
                "real_ip": real_ip,
            } if self._include_headers else None,
            "request_body": request_body_snippet if self._capture_body else None,
        }
        if self._extra_fields:
            record.update(self._extra_fields)

        try:
            await self._emit(record)
        except Exception as e:
            if self._on_error:
                try:
                    self._on_error(e)
                except Exception:
                    pass
        return response

    async def _emit(self, record: dict) -> None:
        # Accept either a provider with .log() or a callable
        if isinstance(self._provider, BaseRequestLogProvider):
            await self._provider.log(record)
        else:
            result = self._provider(record)
            if hasattr(result, "__await__"):
                await result

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _safe_int(value: Optional[str]) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None
