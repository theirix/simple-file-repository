"""
Simple file and photo repository storage.

Backed by filesystem or S3 storages.
"""

from .exceptions import (StorageError,  # noqa: F401
                         StorageNotFoundError,  # noqa: F401
                         StorageNotInitializedError,  # noqa: F401
                         PhotoStorageNotFoundError)  # noqa: F401
from .filestorage import FileStorage  # noqa: F401
from .photostorage import PhotoStorage  # noqa: F401
from .photostorages import PhotoStorages  # noqa: F401
from .s3storage import S3Storage  # noqa: F401
from .storage import Storage  # noqa: F401

__version__ = '0.5.0'
