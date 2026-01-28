"""Dependencies partagees pour l'API."""
import os
from broadcaster import Broadcast

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

broadcast = Broadcast(REDIS_URL)
