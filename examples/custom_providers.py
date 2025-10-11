"""
Exemplos de providers customizados:
- DatabaseAPIKeyProvider: valida API keys em banco (exemplo com asyncpg)
- CIDRIPWhitelistProvider: whitelist com suporte a CIDR

Requisitos extras (instale apenas se for usar):
    pip install asyncpg
"""
import ipaddress
import os
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, status
from starlette.responses import JSONResponse

from os_fastapi_middleware import BaseAPIKeyProvider, BaseIPWhitelistProvider, InMemoryRateLimitProvider, \
    IPWhitelistMiddleware, APIKeyMiddleware, RateLimitMiddleware

try:
    import asyncpg  # type: ignore
except Exception:  # pragma: no cover
    asyncpg = None  # Permite importar o arquivo mesmo sem asyncpg


class DatabaseAPIKeyProvider(BaseAPIKeyProvider):
    """Provider que valida API keys em um banco PostgreSQL usando asyncpg.

    Tabela esperada (exemplo):
        CREATE TABLE api_keys (
            key TEXT PRIMARY KEY,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            user_id TEXT,
            tier TEXT,
            metadata JSONB
        );
    """

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("DATABASE_DSN", "postgresql://user:pass@localhost:5432/app")
        self._pool: Optional["asyncpg.pool.Pool"] = None

    async def _ensure_pool(self):
        if self._pool is None:
            if asyncpg is None:
                raise RuntimeError("asyncpg não está instalado. Instale com: pip install asyncpg")
            self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)

    async def validate_key(self, api_key: str) -> bool:
        await self._ensure_pool()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT active FROM api_keys WHERE key = $1",
                api_key,
            )
            return bool(row and row["active"])  # True se existir e ativo

    async def get_key_metadata(self, api_key: str) -> Optional[Dict[str, Any]]:
        await self._ensure_pool()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT user_id, tier, metadata FROM api_keys WHERE key = $1",
                api_key,
            )
            if not row:
                return None
            # Converte Record para dict simples
            return {
                "user_id": row.get("user_id"),
                "tier": row.get("tier"),
                "metadata": row.get("metadata") or {},
            }


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

api_key_provider = DatabaseAPIKeyProvider(
    dsn=os.getenv("DATABASE_DSN", "postgresql://user:pass@localhost:5432/app")
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
    # Metadados vindos do DatabaseAPIKeyProvider
    meta = getattr(request.state, "api_key_metadata", None) or {}
    return {"api_key_meta": meta}


if __name__ == "__main__":  # Execução local rápida
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
