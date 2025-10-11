from fastapi import HTTPException, status


class SecurityException(HTTPException):
    """Exceção base para erros de segurança."""
    
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class UnauthorizedException(SecurityException):
    """Exceção para falhas de autenticação."""
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "ApiKey"}
        )


class ForbiddenException(SecurityException):
    """Exceção para acesso negado."""
    
    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class RateLimitExceededException(SecurityException):
    """Exceção quando rate limit é excedido."""
    
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)}
        )


class IPNotAllowedException(SecurityException):
    """Exceção quando IP não está na whitelist."""
    
    def __init__(self, ip: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"IP address {ip} is not allowed"
        )