from typing import List, Optional
from pydantic import BaseModel, Field


class APIKeyConfig(BaseModel):
    """Configuração para API Key middleware."""
    
    header_name: str = Field(default="X-API-Key", description="Nome do header da API key")
    exempt_paths: List[str] = Field(
        default=["/health", "/docs", "/redoc", "/openapi.json"],
        description="Paths que não requerem autenticação"
    )
    include_metadata: bool = Field(
        default=False,
        description="Se True, adiciona metadados ao request.state"
    )


class RateLimitConfig(BaseModel):
    """Configuração para Rate Limit middleware."""
    
    requests_per_window: int = Field(
        default=100,
        description="Número de requests permitidos por janela"
    )
    window_seconds: int = Field(
        default=60,
        description="Tamanho da janela em segundos"
    )
    exempt_paths: List[str] = Field(
        default=["/health", "/docs", "/redoc", "/openapi.json"],
        description="Paths sem rate limit"
    )
    add_headers: bool = Field(
        default=True,
        description="Se True, adiciona headers X-RateLimit-*"
    )
    key_prefix: str = Field(
        default="rate_limit",
        description="Prefixo para as chaves de rate limit"
    )


class IPWhitelistConfig(BaseModel):
    """Configuração para IP Whitelist middleware."""
    
    allowed_ips: List[str] = Field(
        default=[],
        description="Lista de IPs permitidos (suporta CIDR)"
    )
    exempt_paths: List[str] = Field(
        default=["/health", "/docs", "/redoc", "/openapi.json"],
        description="Paths sem verificação de IP"
    )
    trust_proxy_headers: bool = Field(
        default=True,
        description="Se True, confia em X-Forwarded-For e X-Real-IP"
    )
    block_on_error: bool = Field(
        default=True,
        description="Se True, bloqueia em caso de erro (fail closed)"
    )


class SecurityConfig(BaseModel):
    """Configuração global de segurança."""
    
    api_key: Optional[APIKeyConfig] = None
    rate_limit: Optional[RateLimitConfig] = None
    ip_whitelist: Optional[IPWhitelistConfig] = None
    
    @classmethod
    def from_env(cls):
        """Carrega configuração de variáveis de ambiente."""
        import os
        
        config = cls()
        
        # API Key config
        if os.getenv("SECURITY_API_KEY_ENABLED", "false").lower() == "true":
            config.api_key = APIKeyConfig(
                header_name=os.getenv("SECURITY_API_KEY_HEADER", "X-API-Key"),
                include_metadata=os.getenv("SECURITY_API_KEY_INCLUDE_METADATA", "false").lower() == "true"
            )
        
        # Rate Limit config
        if os.getenv("SECURITY_RATE_LIMIT_ENABLED", "false").lower() == "true":
            config.rate_limit = RateLimitConfig(
                requests_per_window=int(os.getenv("SECURITY_RATE_LIMIT_REQUESTS", "100")),
                window_seconds=int(os.getenv("SECURITY_RATE_LIMIT_WINDOW", "60"))
            )
        
        # IP Whitelist config
        if os.getenv("SECURITY_IP_WHITELIST_ENABLED", "false").lower() == "true":
            allowed_ips = os.getenv("SECURITY_ALLOWED_IPS", "").split(",")
            config.ip_whitelist = IPWhitelistConfig(
                allowed_ips=[ip.strip() for ip in allowed_ips if ip.strip()]
            )
        
        return config