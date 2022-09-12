import logging
import mimetypes
import os
import subprocess
import tempfile
from typing import Optional
from uuid import UUID

from .exceptions import StorageNotInitializedError
from .storage import Storage


class PhotoStorage(Storage):
    """Photo storage.

    A thin wrapper over file-based `Storage`"""

    logger = logging.getLogger('PhotoStorage')

    def __init__(self, storage: Storage, imagemagick_convert: str):
        self._storage = storage
        self._imagemagick_convert = imagemagick_convert

    def _check_init(self):
        if not self._storage:
            raise StorageNotInitializedError('Call init_app')

    def is_local(self) -> bool:
        return self._storage.is_local()

    def store(self, content: bytes, content_type: Optional[str] = None,
              tags: Optional[dict] = None, override_id: Optional[UUID] = None,
              cache_control: Optional[str] = None) -> UUID:
        self._check_init()
        return self._storage.store(content, content_type=content_type,
                                   tags=tags, override_id=override_id,
                                   cache_control=cache_control)

    def get(self, file_id: UUID) -> bytes:
        self._check_init()
        return self._storage.get(file_id)

    def exists(self, file_id: UUID) -> bool:
        self._check_init()
        return self._storage.exists(file_id)

    def delete(self, file_id: UUID):
        self._check_init()
        return self._storage.delete(file_id)

    def clean(self):
        self._check_init()
        self._storage.clean()

    def get_path(self, file_id: UUID, params: Optional[dict] = None):
        self._check_init()
        return self._storage.get_path(file_id, params)

    def get_mimetype(self, file_id: UUID) -> str:
        self._check_init()
        return self._storage.get_mimetype(file_id)

    def count(self):
        self._check_init()
        return self._storage.count()

    def list(self):
        self._check_init()
        return self._storage.list()

    def _run_imagemagick(self, source_path: str, target_path: str,
                         thumb_size: int):
        image_dim = '{0}x{0}'.format(thumb_size)
        command = [self._imagemagick_convert,
                   source_path,
                   '-auto-orient',
                   '-thumbnail', image_dim,
                   '-gravity', 'center',
                   '-background', 'transparent',
                   '-extent', image_dim,
                   '-strip',
                   target_path]
        subprocess.run(command, shell=False, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def generate_thumbnail(self, image_id: UUID, mime_type: str,
                           thumb_size: int = 200) -> UUID:
        """Generate and store thumbnail for a given image.

         Thumbnail is created using `convert` executable that was passed
         in ctor in `imagemagick_convert`.

         :param image_id: input file id
         :param mime_type: mime type of the thumbnail (can differ with the original file)
         :param thumb_size: width and height of the thumbnail
         :return: thumbnail id
         """
        if not self._imagemagick_convert or not os.path.exists(self._imagemagick_convert):
            raise RuntimeError('Cannot find imagemagick')

        with tempfile.TemporaryDirectory() as tmpdirname:
            extension = mimetypes.guess_extension(mime_type)
            if not extension:
                raise RuntimeError("Extension cannot be deduced for {}".format(mime_type))
            content = self.get(image_id)
            saved_path = os.path.join(tmpdirname,
                                      "saved-{}.{}".format(image_id.hex, extension))
            with open(saved_path, 'wb') as f:
                f.write(content)
            target_file_path = tmpdirname + '/target' + extension
            self._run_imagemagick(saved_path, target_file_path, thumb_size)
            with open(target_file_path, 'rb') as f:
                content = f.read()
                thumbnail_id = self._storage.store(content,
                                                   content_type=mime_type,
                                                   tags=dict(kind='thumb'))
                return thumbnail_id
