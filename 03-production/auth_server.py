"""MCP Server có Authentication — minh hoạ bảo mật cho production.

Server chạy qua HTTP (Streamable HTTP) thay vì stdio, kèm bearer token
verification. Chỉ request mang token hợp lệ mới được phép khám phá và gọi tool.

Luồng hoạt động:
  Client gửi request HTTP kèm header "Authorization: Bearer <token>"
    → MCP SDK tự chạy BearerAuthBackend để xác minh token
    → Token hợp lệ → cho phép truy cập tool
    → Token sai / thiếu → trả về 401/403

Cách chạy:
    pip install -r ../requirements.txt     # từ thư mục gốc repo
    python auth_server.py
    # Server lắng nghe tại http://localhost:8000/mcp
"""

from __future__ import annotations

import os

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer

# --- Token store (production: RBAC với scopes và client identification) ---
VALID_TOKENS: dict[str, dict[str, Any]] = {
    os.environ.get("MCP_AUTH_TOKEN", "civi-token-dev2026"): {
        "client_id": "civi0411-dev",
        "scopes": ["weather:read", "weather:forecast"],
    },
    "dev-token-abc123": {
        "client_id": "standard-dev",
        "scopes": ["weather:read"],
    },
    "prod-key-xyz789": {
        "client_id": "prod-service-gateway",
        "scopes": ["weather:read", "weather:admin", "weather:alerts"],
    },
}


class StaticTokenVerifier(TokenVerifier):
    """Kiểm tra bearer token dựa trên danh sách xác thực và phân quyền RBAC."""

    async def verify_token(self, token: str) -> AccessToken | None:
        info = VALID_TOKENS.get(token)
        if info is None:
            return None
        return AccessToken(
            token=token,
            client_id=info["client_id"],
            scopes=info["scopes"],
        )


# --- MCP Server — logic tool không biết gì về auth --------------------
PORT = int(os.environ.get("MCP_AUTH_PORT", "8000"))

mcp = MCPServer(
    "weather-secure",
    auth=AuthSettings(
        issuer_url=f"http://localhost:{PORT}",
        resource_server_url=f"http://localhost:{PORT}",
    ),
    token_verifier=StaticTokenVerifier(),
)

_MOCK_DB = {
    "Hanoi": "29°C, trời mưa",
    "Haiphong": "33°C, mưa rào",
    "Danang": "30°C, nhiều mây",
}


@mcp.tool()
def get_weather(city: str) -> str:
    """Lấy thời tiết hiện tại của một thành phố."""
    return f"{city}: {_MOCK_DB.get(city, '28°C, không có dữ liệu chi tiết')}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=PORT)

