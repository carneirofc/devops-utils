"""HTTP client for the Azure DevOps REST API (cloud + on-prem Server).

The ``httpx`` import is deferred so importing the package never requires the
``azure`` extra when these tools are unused (mirrors :mod:`devops_utils.mcp.server`).

Credentials are **never** read from the machine (no ``az`` CLI, credential files
or Windows credential store). The bearer token is supplied out-of-band through
the ``AZURE_DEVOPS_TOKEN`` environment variable.
"""

from __future__ import annotations

import base64
import os
from typing import Any

DEFAULT_API_VERSION = "7.1"

# Environment variables the client reads its configuration from.
ENV_ORG_URL = "AZURE_DEVOPS_ORG_URL"
ENV_TOKEN = "AZURE_DEVOPS_TOKEN"  # nosec B105 - env var name, not a secret
ENV_AUTH_SCHEME = "AZURE_DEVOPS_AUTH_SCHEME"
ENV_API_VERSION = "AZURE_DEVOPS_API_VERSION"


class AzureDevOpsError(RuntimeError):
    """Raised when the Azure DevOps API returns a non-2xx response."""

    def __init__(self, status_code: int, method: str, url: str, body: str) -> None:
        self.status_code = status_code
        self.method = method
        self.url = url
        self.body = body
        super().__init__(f"{method} {url} -> HTTP {status_code}: {body}")


def _require_httpx() -> "Any":
    try:
        import httpx
    except ModuleNotFoundError as exc:  # pragma: no cover - trivial guard
        raise SystemExit(
            "The Azure DevOps tools require the 'azure' extra. "
            "Install it with: pip install devops-utils[azure]"
        ) from exc
    return httpx


class AzureDevOpsClient:
    """Thin wrapper over ``httpx`` for the Azure DevOps REST API.

    Args:
        org_url: Base URL. Cloud ``https://dev.azure.com/{org}`` or on-prem
            ``https://server/tfs/{collection}``. A trailing slash is stripped.
        token: Bearer token or Personal Access Token (see ``auth_scheme``).
        auth_scheme: ``"bearer"`` sends ``Authorization: Bearer <token>``;
            ``"pat"`` sends ``Authorization: Basic base64(":" + token)`` which is
            how Azure DevOps expects a raw PAT.
        api_version: REST ``api-version`` query value. Lower it for older
            on-prem servers (e.g. ``"6.0"``).
    """

    def __init__(
        self,
        org_url: str,
        token: str,
        auth_scheme: str = "bearer",
        api_version: str = DEFAULT_API_VERSION,
        transport: "Any | None" = None,
    ) -> None:
        if not org_url or not org_url.strip():
            raise ValueError("org_url is required")
        if not token or not token.strip():
            raise ValueError("token is required")
        scheme = auth_scheme.strip().lower()
        if scheme not in ("bearer", "pat"):
            raise ValueError(
                f"auth_scheme must be 'bearer' or 'pat', got {auth_scheme!r}"
            )

        self.org_url = org_url.strip().rstrip("/")
        self.token = token.strip()
        self.auth_scheme = scheme
        self.api_version = api_version.strip() or DEFAULT_API_VERSION
        # Optional httpx transport, used by tests to mock the network.
        self._transport = transport

    @classmethod
    def from_env(cls) -> "AzureDevOpsClient":
        """Build a client from environment variables.

        Reads ``AZURE_DEVOPS_ORG_URL`` and ``AZURE_DEVOPS_TOKEN`` (both required),
        and optional ``AZURE_DEVOPS_AUTH_SCHEME`` (default ``bearer``) and
        ``AZURE_DEVOPS_API_VERSION`` (default ``7.1``).
        """
        org_url = os.environ.get(ENV_ORG_URL, "")
        token = os.environ.get(ENV_TOKEN, "")
        missing = [
            name
            for name, value in ((ENV_ORG_URL, org_url), (ENV_TOKEN, token))
            if not value.strip()
        ]
        if missing:
            raise ValueError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ". Set them before using the Azure DevOps tools."
            )
        return cls(
            org_url=org_url,
            token=token,
            auth_scheme=os.environ.get(ENV_AUTH_SCHEME, "bearer"),
            api_version=os.environ.get(ENV_API_VERSION, DEFAULT_API_VERSION),
        )

    def _auth_header(self) -> str:
        if self.auth_scheme == "pat":
            encoded = base64.b64encode(f":{self.token}".encode()).decode("ascii")
            return f"Basic {encoded}"
        return f"Bearer {self.token}"

    def _url(self, path: str) -> str:
        return f"{self.org_url}/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        content: bytes | None = None,
        content_type: str | None = None,
        api_version: str | None = None,
        base_url: str | None = None,
    ) -> Any:
        """Perform a request and return the parsed JSON body (or ``None``).

        ``api-version`` is injected into the query string unless already present.
        ``base_url`` overrides ``org_url`` for APIs served from a different host
        (e.g. cloud code search on ``almsearch.dev.azure.com``).
        Raises :class:`AzureDevOpsError` for any non-2xx response.
        """
        httpx = _require_httpx()

        query: dict[str, Any] = dict(params or {})
        query.setdefault("api-version", api_version or self.api_version)

        headers = {"Authorization": self._auth_header(), "Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        elif json is not None:
            headers["Content-Type"] = "application/json"

        base = (base_url or self.org_url).rstrip("/")
        url = f"{base}/{path.lstrip('/')}"
        with httpx.Client(timeout=30.0, transport=self._transport) as http:
            response = http.request(
                method,
                url,
                params=query,
                json=json,
                content=content,
                headers=headers,
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise AzureDevOpsError(
                response.status_code, method, str(response.url), response.text
            )
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text
