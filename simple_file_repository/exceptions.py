class StorageError(RuntimeError):
    """Generic exception class for the library."""


class StorageNotFoundError(StorageError):
    """File is not found."""


class StorageNotInitializedError(StorageError):
    """Storage is not properly initiailized."""


class PhotoStorageNotFoundError(StorageError):
    """Photo storage is not registered in :class:`~simple_file_repository.PhotoStorages`."""
