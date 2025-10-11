# Installation

This project provides security middlewares for FastAPI under the public import package `os_fastapi_middleware`. Install it via pip.

## Requirements
- Python >= 3.8
- FastAPI >= 0.100.0
- Starlette >= 0.27.0

## Basic installation

```bash
pip install os-fastapi-middleware
```

## Optional extras

- Redis for distributed rate limiting:

```bash
pip install os-fastapi-middleware[redis]
```

This installs `redis>=5.0.0` and enables the `RedisRateLimitProvider`.

## Quick verification

After installation, verify the import works:

```bash
python -c "import os_fastapi_middleware as m; print(getattr(m, '__version__', 'ok'))"
```

If no error is shown, the installation is OK.

## Install from source

1. Clone the repository

```bash
git clone https://github.com/seu-usuario/os-fastapi-middleware.git
cd os-fastapi-middleware
```

2. Install in development mode (optional, with testing tools):

```bash
pip install -e .[dev]
```

3. Run the tests to ensure everything is working:

```bash
pytest -q
```

## Compatibility

- Operating systems: Linux, macOS and Windows
- Python versions: 3.8, 3.9, 3.10, 3.11

If you find any installation issues, please open an issue with environment details and error logs.
