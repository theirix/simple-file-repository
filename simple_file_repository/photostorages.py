import logging
from typing import Optional

from .exceptions import PhotoStorageNotFoundError, StorageNotInitializedError
from .filestorage import FileStorage
from .photostorage import PhotoStorage
from .s3storage import S3Storage


class PhotoStorages:
    """Photo storages for multiple databases.

    Implemented as composition over file-based `Storage`"""

    logger = logging.getLogger('PhotoStorages')

    def __init__(self):
        self._storages = None
        self._storage_directory = None

    # False positive for Python 3.9, see pylint bug 3882
    # pylint: disable=unsubscriptable-object
    def init_app(self, names: [str], storage_directory: str,
                 imagemagick_convert: str,
                 names_for_s3: [str],
                 bucket: str,
                 region: str, access_key_id: str, secret_access_key: str,
                 endpoint_url: Optional[str],
                 default_cache_control: Optional[str],
                 config=None
                 ):
        """Initialize photo storages.

         :param names: a list of database names
         :param storage_directory: a root storage directory
         :param imagemagick_convert: path to `convert` executable
         :param names_for_s3: a list of database names that will be stored in `S3Storage`
         :param bucket: see :class:`S3Storage` for documentation
         :param region: see :class:`S3Storage` for documentation
         :param access_key_id: see :class:`S3Storage` for documentation
         :param secret_access_key: see :class:`S3Storage` for documentation
         :param endpoint_url: see :class:`S3Storage` for documentation
         :param default_cache_control: see :class:`S3Storage` for documentation
         """
        self._storage_directory = storage_directory

        self._storages = {}
        for name in names:
            if name in names_for_s3:
                storage = S3Storage(database=name, bucket=bucket, region=region,
                                    access_key_id=access_key_id,
                                    secret_access_key=secret_access_key,
                                    endpoint_url=endpoint_url,
                                    default_cache_control=default_cache_control,
                                    config=config,
                                    )
            else:
                storage = FileStorage(storage_directory=storage_directory,
                                      database=name,
                                      stripes=None)
            photo_storage = PhotoStorage(storage=storage,
                                         imagemagick_convert=imagemagick_convert)
            self._storages[name] = photo_storage

    def __getitem__(self, item: str) -> PhotoStorage:
        """Extract a photo storage by database name.

         :param item: a database name
         :return: a photo storage"""
        if not self._storage_directory:
            raise StorageNotInitializedError('Call init_app')
        if item in self._storages:
            return self._storages[item]
        raise PhotoStorageNotFoundError('PhotoStorage named {} not found in {}'.
                                        format(item, repr(self)))

    def clean(self):
        """Clean all underlying storages."""
        for storage in self._storages.values():
            storage.clean()

    def __repr__(self) -> str:
        if self._storages:
            return "<PhotoStorages: {} at dir {}>". \
                format(','.join(self._storages.keys()),
                       self._storage_directory)
        return "<PhotoStorages: empty>"
