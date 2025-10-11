# Publishing fastapi-security-middleware to the public (PyPI)

This guide walks you through releasing this library publicly. It covers local builds, TestPyPI dry-runs, real PyPI uploads, and optional CI-based Trusted Publishing.

Prerequisites
- Python 3.8+ and pip
- A PyPI account (https://pypi.org) and optionally a TestPyPI account (https://test.pypi.org)
- twine and build installed locally
  - python -m pip install --upgrade build twine

1) Check and complete project metadata
- Edit pyproject.toml and replace placeholders with real data:
  - project.name: the final package name (e.g., fastapi-security-middleware)
  - project.version: follow SemVer (e.g., 1.0.0). Bump for every release
  - project.authors: your name/email
  - project.urls: set real repository, homepage, docs, issues URLs
  - project.classifiers: adjust Development Status and supported Python versions if needed
- Ensure README.md exists; it’s used for the long description
- License is set to MIT by default; update if necessary

2) Verify package layout
- Your package lives at fastapi_security/ in the repo root and pyproject.toml uses setuptools as the backend.
- Setuptools will auto-discover packages by default. No src/ mapping is used here; you don’t need changes.
- If you later migrate to a src layout, you must configure package_dir/find options accordingly.

3) Build distributions
- Clean previous build artifacts (optional):
  - rm -rf build/ dist/ *.egg-info
- Build sdist and wheel:
  - python -m build
- Verify artifacts are created in dist/: .tar.gz and .whl

4) Check the artifacts
- Run Twine’s checks locally:
  - twine check dist/*
- Fix any errors (e.g., malformed long description) before uploading

5) Dry run on TestPyPI (recommended)
- Create an API token on TestPyPI and save it as TEST_PYPI_TOKEN
- Upload to TestPyPI:
  - twine upload --repository-url https://test.pypi.org/legacy/ -u __token__ -p $TEST_PYPI_TOKEN dist/*
- Install from TestPyPI in a fresh virtualenv to validate:
  - python -m venv .venv-test
  - source .venv-test/bin/activate  # or .venv-test\Scripts\activate on Windows
  - python -m pip install --upgrade pip
  - python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple fastapi-security-middleware
  - python -c "import fastapi_security; print(fastapi_security.__version__)"

6) Publish to PyPI
- Create a PyPI API token and store it locally as PYPI_TOKEN
- Upload:
  - twine upload -u __token__ -p $PYPI_TOKEN dist/*
- Confirm the release at https://pypi.org/project/fastapi-security-middleware/

7) Tag the release in Git
- Use an annotated tag that matches your version:
  - git tag -a v1.0.0 -m "Release v1.0.0"
  - git push origin v1.0.0

8) Optional: GitHub Actions Trusted Publishing (no API tokens)
- PyPI supports OIDC-based Trusted Publishing to avoid storing secrets. High-level steps:
  1. Create a new PyPI project named fastapi-security-middleware and enable "Trusted Publishers"; add your GitHub repo as a publisher (Actions)
  2. Add a workflow file like .github/workflows/release.yml that builds on tag and uses pypa/gh-action-pypi-publish

Example workflow:

name: Release
on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  build-and-publish:
    permissions:
      id-token: write  # required for trusted publishing
      contents: read
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install build tools
        run: python -m pip install --upgrade build
      - name: Build
        run: python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          skip-existing: true

Notes and tips
- Versioning: choose Semantic Versioning. Bump patch for fixes, minor for new features, major for breaking changes
- Changelog: maintain a CHANGELOG.md and reference it in GitHub releases
- Pre-release: use pre-release versions (e.g., 1.1.0rc1) for candidates; Twine will upload them; pip can install pre-releases with --pre
- Test matrix: before releasing, run tests locally: python -m pip install -e .[dev] && pytest
- Readme badges: add PyPI version, Python versions, license, and CI status badges to README.md
- Package import path: users will import as `from fastapi_security.middleware import APIKeyMiddleware`, so confirm __init__ exports are in place (already present)

If you want, we can add a GitHub Actions workflow file for releases now. Open an issue and we’ll wire it up to use Trusted Publishing or an API token.