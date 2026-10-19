from app.config import settings

for name in ["JINA_API_KEY", "OPENAI_API_KEY", "PORTKEY_API_KEY", "PORTKEY_PRIMARY_CONFIG_ID"]:
    v = getattr(settings, name)
    print(f"{name}: length={len(v)}, starts with '{v[:4]}', stray_spaces={v != v.strip()}")