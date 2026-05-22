from langchain.chat_models import init_chat_model

gemini_flash_3_1_lite = init_chat_model(
    "gemini-3.1-flash-lite",
    model_provider="google-genai",
    temperature=0.5,
    timeout=600,
    max_tokens=1000,
    streaming=False,
)
