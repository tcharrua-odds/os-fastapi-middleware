"""
Exemplos de providers customizados:
- CIDRIPWhitelistProvider: whitelist com suporte a CIDR
"""
import ipaddress
from typing import List

from fastapi import FastAPI, status
from starlette.responses import JSONResponse

from os_fastapi_middleware import BaseIPWhitelistProvider, InMemoryRateLimitProvider, InMemoryAPIKeyProvider, \
    IPWhitelistMiddleware, APIKeyMiddleware, RateLimitMiddleware


class CIDRIPWhitelistProvider(BaseIPWhitelistProvider):
    """Provider de whitelist com suporte a IPs individuais e ranges CIDR.

    Exemplo:
        allowed=["127.0.0.1", "10.0.0.0/8", "192.168.1.0/24"]
    """

    def __init__(self, allowed: List[str]):
        self._nets: List[ipaddress._BaseNetwork] = []
        self._singles: List[ipaddress._BaseAddress] = []
        for item in allowed:
            if "/" in item:
                self._nets.append(ipaddress.ip_network(item, strict=False))
            else:
                self._singles.append(ipaddress.ip_address(item))

    async def is_ip_allowed(self, ip: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        # IPs individuais
        if any(addr == s for s in self._singles):
            return True
        # Ranges
        if any(addr in net for net in self._nets):
            return True
        return False

    async def get_allowed_ips(self) -> List[str]:  # Opcional
        # Retorna apenas representação string (para debug/doc)
        values = [str(s) for s in self._singles]
        values += [str(n) for n in self._nets]
        return values


# Exemplo de composição em um app FastAPI usando os providers acima
app = FastAPI(title="Custom Providers Example")

api_key_provider = InMemoryAPIKeyProvider(
    valid_keys={
        "account_alice": "secret-key-123",
        "account_bob": "secret-key-456",
    }
)

ip_whitelist_provider = CIDRIPWhitelistProvider(
    allowed=[
        "127.0.0.1",
        "10.0.0.0/8",
        "192.168.1.0/24",
    ]
)

rate_limit_provider = InMemoryRateLimitProvider()


# Handlers opcionais

def on_blocked(request, ip: str):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": f"IP {ip} bloqueado pela política de segurança"},
    )


app.add_middleware(IPWhitelistMiddleware, provider=ip_whitelist_provider, on_blocked=on_blocked)
app.add_middleware(APIKeyMiddleware, provider=api_key_provider, include_metadata=True)
app.add_middleware(RateLimitMiddleware, provider=rate_limit_provider, requests_per_window=60, window_seconds=60)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/me")
async def me(request):
    # Metadados vindos do InMemoryAPIKeyProvider
    meta = getattr(request.state, "api_key_metadata", None) or {}
    return {"api_key_meta": meta}


if __name__ == "__main__":  # Execução local rápida
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
