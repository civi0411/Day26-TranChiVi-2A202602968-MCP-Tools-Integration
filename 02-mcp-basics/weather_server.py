"""MCP SERVER minh hoạ — công bố tool `get_weather` qua giao thức MCP.

Khác với function calling: tool nằm ở một server ĐỘC LẬP. Server tự "khai
báo" tool của mình; bất kỳ MCP client nào (Claude Code, Claude Desktop,
Cursor, hoặc weather_client.py) cũng cắm vào dùng được mà không cần biết
code bên trong.

Schema của tool được TỰ ĐỘNG sinh ra từ type hints + docstring.

Chạy trực tiếp:
    pip install -r ../requirements.txt
    python weather_server.py

Đăng ký với Claude Code (làm 1 lần, dùng mãi):
    claude mcp add weather -- python /đường/dẫn/tới/weather_server.py
"""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("weather")

_MOCK_DB = {
    "Hanoi": {"temp": "29°C", "cond": "trời mưa nhẹ", "hum": "82%", "wind": "12 km/h Đông Nam"},
    "Haiphong": {"temp": "33°C", "cond": "mưa rào rải rác", "hum": "79%", "wind": "16 km/h Đông"},
    "Danang": {"temp": "30°C", "cond": "nhiều mây, biển êm", "hum": "74%", "wind": "10 km/h Đông Bắc"},
    "Ho Chi Minh": {"temp": "33°C", "cond": "nắng gián đoạn, chiều dông", "hum": "76%", "wind": "15 km/h Tây Nam"},
    "Da Lat": {"temp": "19°C", "cond": "se lạnh, sương mù nhẹ", "hum": "88%", "wind": "8 km/h"},
}


@mcp.resource("weather://catalog")
def get_station_catalog() -> str:
    """[MCP Resource] Cung cấp danh mục trạm quan trắc thời tiết và metadata."""
    stations = list(_MOCK_DB.keys())
    return f"Trạm quan trắc trực tuyến ({len(stations)} trạm): {', '.join(stations)} | Tần suất cập nhật: 15 phút/lần."


@mcp.tool()
def get_weather(city: str) -> str:
    """Lấy thời tiết hiện tại của một thành phố."""
    clean_city = city.strip().title()
    match = _MOCK_DB.get(clean_city)
    if not match:
        for k, v in _MOCK_DB.items():
            if k.lower() in city.lower():
                match = v
                clean_city = k
                break
    if match:
        return f"{clean_city}: {match['temp']}, {match['cond']} (Độ ẩm: {match['hum']}, Gió: {match['wind']})"
    return f"{city}: 28°C, thời tiết thuận lợi (trạm dự phòng)"


if __name__ == "__main__":
    mcp.run()  # mặc định chạy qua stdio
