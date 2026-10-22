"""Bound idle inference buffers without changing model computation."""
import mlx.core as mx

IDLE_CACHE_BUDGET = 1024**3


def release_inference_cache() -> bool:
    """Check after a token's blocking item(); clear only above the idle budget.

    Only unused allocator buffers are cleared. Active weights and KV state
    remain intact. Smaller decode buffers can be reused normally. Run inside
    the existing scan lock, never on another thread; do not alter process-wide
    cache/memory/wired limits. This is not a cap on active or peak memory.
    """
    if mx.get_cache_memory() > IDLE_CACHE_BUDGET:
        mx.clear_cache()
        return True
    return False
