import sys
sys.path.append('.')

try:
    from app.infrastructure.llm.openai_client import get_llm_client
    client = get_llm_client()
    print("enabled:", client.enabled)
    print("api_key set:", bool(client.api_key))
    print("api_key prefix:", (client.api_key[:8] + "...") if client.api_key else "NONE")
    print("model:", client.model)
    print("base_url:", getattr(client, "BASE_URL", None))

    result = client.generate_sync(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say hello in one sentence.",
    )
    print("success:", getattr(result, "success", None))
    print("error:", getattr(result, "error", None))
    print("content:", getattr(result, "content", None))
    print("model_used:", getattr(result, "model", None))
except Exception as e:
    import traceback
    traceback.print_exc()
