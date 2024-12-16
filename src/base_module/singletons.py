import abc
import threading


class ThreadIsolatedSingleton(abc.ABCMeta):
    """."""

    _instances = threading.local()

    def __call__(cls, *args, **kwargs):
        """."""
        if not hasattr(cls._instances, "heap"):
            cls._instances.heap = {}
        if cls not in cls._instances.heap:
            cls._instances.heap[cls] = super(ThreadIsolatedSingleton, cls).__call__(
                *args, **kwargs
            )
        return cls._instances.heap[cls]
