from redis import Redis
from redis.exceptions import RedisError

from .config import settings
from .vocabulary import VocabularyManager

vocab_manager: VocabularyManager = VocabularyManager(settings.VOCAB_DIR)

# Each uvicorn worker holds its own in-process vocab copy, so a reload via
# /api/admin/reload-vocab only reaches the worker that served it. The endpoint
# bumps this shared counter; other workers compare it against their local copy
# on vocab-reading requests and lazily reload when stale.
VOCAB_VERSION_KEY = "vocab_version"
_local_vocab_version: int | None = None


def sync_vocab(redis: Redis) -> None:
    global _local_vocab_version
    try:
        raw = redis.get(VOCAB_VERSION_KEY)
    except RedisError:
        return  # Redis down — keep serving the current in-memory vocab
    remote = int(raw) if raw else 0
    if _local_vocab_version is None and remote == 0:
        # First check and no reload has ever been requested: the boot-time
        # disk load is current.
        _local_vocab_version = 0
        return
    # On a worker's first check after a past bump we can't tell whether the
    # bump predates our boot, so reload; a disk re-read is cheap and always
    # gives the current state.
    if remote != _local_vocab_version:
        vocab_manager.load_all()
        _local_vocab_version = remote


def bump_vocab_version(redis: Redis) -> None:
    global _local_vocab_version
    _local_vocab_version = int(redis.incr(VOCAB_VERSION_KEY))
