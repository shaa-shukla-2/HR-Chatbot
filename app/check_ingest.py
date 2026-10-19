from qdrant_client import QdrantClient
from app.config import settings

c = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
name = settings.QDRANT_COLLECTION
print("collection:", name)
print("points:", c.count(name, exact=True).count)

points, _ = c.scroll(name, limit=3, with_payload=True, with_vectors=False)
for p in points:
    print("-", str(p.payload)[:200])