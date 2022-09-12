import glob
import logging
import os
import shutil
import tempfile
from typing import Iterable, Optional
from uuid import UUID, uuid4

from .exceptions import StorageError, StorageNotFoundError, StorageNotInitializedError
from .storage import Storage
from .utils import guess_mime_type


class DefaultParams:
    """Default parameters"""
    STRIPES = 1000


class FileStorage(Storage):
    """Filesystem-based storage"""

    logger = logging.getLogger('FileStorage')

    def __init__(self, storage_directory: Optional[str] = None,
                 database: Optional[str] = None,
                 stripes: Optional[int] = None, initialize: bool = True,
                 file_perm=0o660, dir_perm=0o770):
        """Constructs FileStorage instance.

         If `initialize` is set to `True`, initialization is deferred
         until :meth:`init_app` is called.

         :param storage_directory: a root storage directory
         :param database: a database name
         :param stripes: count of directory stripes
         :param initialize: initialize immediately if `True`
         :param file_perm: permissions for created files
         :param dir_perm: permissions for created dirs
         """
        self.storage_directory = storage_directory
        self.database = database
        self.database_directory = None
        self.stripe_size = stripes or DefaultParams.STRIPES
        self._file_perm = file_perm
        self._dir_perm = dir_perm

        if self.storage_directory and initialize:
            self.init_app()

    def init_app(self, storage_directory: Optional[str] = None,
                 database: Optional[str] = None,
                 stripes: Optional[int] = None):
        """Initialize instance if `initialize=False` was passed in ctor."""
        self.storage_directory = self.storage_directory or storage_directory
        self.database = self.database or database
        self.stripe_size = self.stripe_size or stripes

        if not self.stripe_size or self.stripe_size < 1:
            raise ValueError('Invalid stripe size ' + str(self.stripe_size))
        if not self.database or not self.database.strip():
            raise ValueError('Invalid database name ' + self.database)
        try:
            self._initialize_storage()
        except Exception as e:
            raise StorageError("Cannot create dirs: {}".format(str(e))) from e

    def _makedir(self, path):
        if not os.path.isdir(path):
            os.mkdir(path)
            os.chmod(path, self._dir_perm)

    def _initialize_storage(self):
        self.database_directory = os.path.join(self.storage_directory, self.database)
        self._makedir(self.storage_directory)
        self._makedir(self.database_directory)

    @staticmethod
    def _generate_file_id():
        file_id = uuid4()
        return file_id

    def _check_init(self):
        if not self.database_directory or not os.path.isdir(self.database_directory):
            raise StorageNotInitializedError('Storage is not initialized')

    def _select_stripe(self, file_id: UUID) -> str:
        stripe_name = 'stripe_{}'.format(file_id.int % self.stripe_size)
        return os.path.join(self.database_directory, stripe_name)

    def _select_or_create_stripe(self, file_id: UUID) -> str:
        stripe_directory = self._select_stripe(file_id)
        self._makedir(stripe_directory)
        return stripe_directory

    def is_local(self) -> bool:
        return True

    def get(self, file_id: UUID) -> bytes:
        stripe_dir = self._select_stripe(file_id)
        blob_path = os.path.join(stripe_dir, file_id.hex + '.bin')
        if not os.path.isfile(blob_path):
            raise StorageNotFoundError('File {} does not exist'.format(file_id))
        try:
            with open(blob_path, 'rb') as f:
                content = f.read()
            return content
        except Exception as e:  # pragma: no cover
            raise StorageError(e) from e

    def get_path(self, file_id: UUID, params: Optional[dict] = None) -> str:
        stripe_dir = self._select_stripe(file_id)
        blob_path = os.path.join(stripe_dir, file_id.hex + '.bin')
        if not os.path.isfile(blob_path):
            raise StorageNotFoundError('File {} does not exist'.format(file_id))
        return blob_path

    def exists(self, file_id: UUID) -> bool:
        self._check_init()
        stripe_dir = self._select_stripe(file_id)
        blob_path = os.path.join(stripe_dir, file_id.hex + '.bin')
        return os.path.isfile(blob_path)

    def store(self, content: bytes, content_type: Optional[str] = None,
              tags: Optional[dict] = None, override_id: Optional[UUID] = None,
              cache_control: Optional[str] = None) -> UUID:
        # early check
        self._check_init()
        file_id = override_id if override_id else self._generate_file_id()
        try:
            # detect target path
            stripe_dir = self._select_or_create_stripe(file_id)
            blob_path = os.path.join(stripe_dir, file_id.hex + '.bin')
            if os.path.isfile(blob_path):
                raise StorageError('File {} already stored'.format(file_id))

            # open a temporary file
            tmp_fd, tmp_path = tempfile.mkstemp(prefix='sfr-', suffix='.tmp')
            try:
                os.write(tmp_fd, content)
                os.close(tmp_fd)
            except Exception as e:  # pragma: no cover
                # remove tmp file
                os.unlink(tmp_path)
                raise StorageError(e) from e
            # move to target path
            shutil.move(tmp_path, blob_path)
            os.chmod(blob_path, self._file_perm)
            return file_id
        except StorageError:
            raise
        except Exception as e:  # pragma: no cover
            raise StorageError(e) from e

    def delete(self, file_id: UUID):
        stripe_dir = self._select_stripe(file_id)
        blob_path = os.path.join(stripe_dir, file_id.hex + '.bin')
        if not os.path.isfile(blob_path):
            raise StorageNotFoundError('File {} does not exist'.format(file_id))
        try:
            os.unlink(blob_path)
        except Exception as e:  # pragma: no cover
            raise StorageError(e) from e

    def get_mimetype(self, file_id: UUID) -> str:
        try:
            with open(self.get_path(file_id), 'rb') as f:
                peek = f.read()[0:500]
                return guess_mime_type(peek)
        except StorageError:
            raise
        except Exception as e:  # pragma: no cover
            raise StorageError(e) from e

    def count(self) -> int:
        self._check_init()
        try:
            return len(glob.glob(self.database_directory + '/*/*.bin'))
        except Exception as e:  # pragma: no cover
            raise StorageError(e) from e

    def list(self) -> Iterable[str]:
        self._check_init()
        try:
            return (path.split('/')[-1][0:-4] for path in
                    glob.glob(self.database_directory + '/*/*.bin'))
        except Exception as e:  # pragma: no cover
            raise StorageError(e) from e

    def clean(self):
        if not self.database_directory:
            return
        try:
            for file in glob.glob(self.database_directory + '/*/*.bin'):
                os.remove(file)
            if os.path.isdir(self.database_directory):
                shutil.rmtree(self.database_directory)
        except Exception as e:  # pragma: no cover
            raise StorageError(e) from e

    def __repr__(self) -> str:
        return "FileStorage db={}".format(self.database)
