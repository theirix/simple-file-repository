import abc
from abc import ABCMeta, abstractmethod
from typing import Iterable, Optional
from uuid import UUID


class Storage(abc.ABC, metaclass=ABCMeta):
    """Generic storage for files."""

    @abstractmethod
    def is_local(self) -> bool:
        """Retrieve true if get_path returns local filesystem path."""

    @abstractmethod
    def get(self, file_id: UUID) -> bytes:
        """Retrieve file by file_id."""

    @abstractmethod
    def get_path(self, file_id: UUID, params: Optional[dict] = None) -> str:
        """Retrieve file by file_id."""

    @abstractmethod
    def exists(self, file_id: UUID) -> bool:
        """Check if the file by file_id exists."""

    @abstractmethod
    def store(self, content: bytes, content_type: Optional[str] = None,
              tags: Optional[dict] = None, override_id: Optional[UUID] = None,
              cache_control: Optional[str] = None) -> UUID:
        """Stores file and returns a file-id."""

    @abstractmethod
    def get_mimetype(self, file_id: UUID) -> str:
        """Retrieve mimetype by file_id."""

    @abstractmethod
    def delete(self, file_id: UUID):
        """Deletes a file by file_id."""

    @abstractmethod
    def count(self) -> int:
        """Returns file count in storage.

         **NOTE**: Should be used only for tests or debugging."""

    @abstractmethod
    def list(self) -> Iterable[str]:
        """Returns file list in storage.

         **NOTE**: Should be used only for tests or debugging."""

    @abstractmethod
    def clean(self):
        """Delete all items in storage.

         **NOTE**: Should be used only for tests or debugging."""
