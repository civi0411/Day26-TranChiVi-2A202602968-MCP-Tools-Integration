"""Minh hoạ FUNCTION CALLING thuần với Google Gemini SDK.

Tool `get_weather` được định nghĩa schema thủ công VÀ thực thi ngay trong
chính file app này. Model chỉ QUYẾT ĐỊNH gọi tool nào; app mới là nơi chạy.

Cách chạy:
    pip install -r ../requirements.txt
    export GEMINI_API_KEY=...
    python weather_function_calling.py
"""

from google import genai
from google.genai import types

client = genai.Client()

import os

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp (🌧️ 🌤️ 💨 💧). "
    "Tóm tắt ngắn gọn, dễ hiểu, và đưa ra lời khuyên thực tế "
    "(ví dụ: mang ô, mặc áo mỏng, ...)."
)

# 1. App tự định nghĩa schema của tool
get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Lấy thời tiết hiện tại của một thành phố",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING, description="Tên thành phố"
            )
        },
        required=["city"],
    ),
)

TOOLS = [types.Tool(function_declarations=[get_weather_declaration])]


# 2. App tự thực thi tool với bộ chuẩn hoá tên thành phố và dữ liệu thời tiết chi tiết
_CITY_ALIASES = {
    "hanoi": "Hà Nội", "ha noi": "Hà Nội", "hn": "Hà Nội", "thu do": "Hà Nội",
    "danang": "Đà Nẵng", "da nang": "Đà Nẵng", "dn": "Đà Nẵng",
    "hochiminh": "Hồ Chí Minh", "ho chi minh": "Hồ Chí Minh", "saigon": "Hồ Chí Minh", "sai gon": "Hồ Chí Minh", "tphcm": "Hồ Chí Minh",
    "haiphong": "Hải Phòng", "hai phong": "Hải Phòng",
    "cantho": "Cần Thơ", "can tho": "Cần Thơ",
}

_MOCK_METEO_DB = {
    "Hà Nội": {
        "nhiệt_độ": "29°C",
        "cảm_giác_như": "31°C",
        "thời_tiết": "trời mưa nhẹ, mây rải rác",
        "độ_ẩm": "82%",
        "chỉ_số_uv": 4.0,
        "gió": {"hướng": "Đông Nam", "tốc_độ": "12 km/h"},
        "khuyến_nghị": "Nên mang theo ô/dù khi ra ngoài, đường ẩm ướt.",
    },
    "Hồ Chí Minh": {
        "nhiệt_độ": "33°C",
        "cảm_giác_như": "36°C",
        "thời_tiết": "nắng nhiệt đới, chiều có mưa dông",
        "độ_ẩm": "75%",
        "chỉ_số_uv": 8.0,
        "gió": {"hướng": "Tây Nam", "tốc_độ": "15 km/h"},
        "khuyến_nghị": "Thời tiết oi bức, hạn chế tiếp xúc nắng gắt giữa trưa.",
    },
    "Đà Nẵng": {
        "nhiệt_độ": "30°C",
        "cảm_giác_như": "32°C",
        "thời_tiết": "nhiều mây, gió biển mát",
        "độ_ẩm": "74%",
        "chỉ_số_uv": 6.0,
        "gió": {"hướng": "Đông", "tốc_độ": "10 km/h"},
        "khuyến_nghị": "Thời tiết lý tưởng cho các hoạt động ngoài trời.",
    },
}


def _normalize_city_name(city: str) -> str:
    """Chuẩn hoá tên thành phố đầu vào từ LLM (hỗ trợ không dấu, viết tắt, alias)."""
    import unicodedata
    import re
    cleaned = unicodedata.normalize('NFKD', city).encode('ASCII', 'ignore').decode('utf-8')
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', cleaned).strip().lower()
    return _CITY_ALIASES.get(cleaned, city.strip())


def get_weather(city: str) -> str:
    """Trả về dữ liệu khí tượng chuẩn hoá của *city* dưới dạng JSON."""
    import json
    norm_city = _normalize_city_name(city)
    data = _MOCK_METEO_DB.get(norm_city)
    if not data:
        data = {
            "nhiệt_độ": "28°C",
            "cảm_giác_như": "29°C",
            "thời_tiết": "thời tiết ôn hoà, mây thoáng",
            "độ_ẩm": "70%",
            "chỉ_số_uv": 5.0,
            "gió": {"hướng": "Đông", "tốc_độ": "10 km/h"},
            "khuyến_nghị": "Thời tiết thuận lợi cho công việc và di chuyển.",
        }
    return json.dumps({"city": norm_city, **data}, ensure_ascii=False)


def run(prompt: str) -> str:
    """Gửi *prompt* tới Gemini, tự động xử lý function calling và trả về câu trả lời cuối."""
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]

    # 3. Gọi model — model quyết định có gọi tool hay không
    resp = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            tools=TOOLS,
            system_instruction=SYSTEM_INSTRUCTION,
        ),
    )

    # 4. Vòng lặp: nếu model yêu cầu tool, app TỰ THỰC THI rồi đưa kết quả trả lại
    while resp.function_calls:
        contents.append(resp.candidates[0].content)

        function_responses = []
        for fc in resp.function_calls:
            print(f"  [model yêu cầu] {fc.name}({fc.args})")
            result = get_weather(**fc.args)  # <-- app thực thi tool
            print(f"  [app thực thi]  -> {result}")
            function_responses.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )

        # Gửi kết quả tool trả về cho model
        contents.append(types.Content(role="user", parts=function_responses))
        resp = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                tools=TOOLS,
                system_instruction=SYSTEM_INSTRUCTION,
            ),
        )

    # 5. Model tổng hợp câu trả lời cuối
    return resp.text


if __name__ == "__main__":
    question = "Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"
    print(f"User: {question}\n")
    print("Trả lời:", run(question))
