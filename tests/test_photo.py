import logging
import os

import pytest

from simple_file_repository.exceptions import StorageNotInitializedError, PhotoStorageNotFoundError
from simple_file_repository.filestorage import FileStorage
from simple_file_repository.photostorage import PhotoStorage
from simple_file_repository.photostorages import PhotoStorages


def test_write(file_storage_db):
    storage = PhotoStorage(storage=file_storage_db,
                           imagemagick_convert='')
    content = 'hello world'.encode('utf-8')
    file_id = storage.store(content)
    assert file_id.int
    assert storage.count() == 1
    content_read = storage.get(file_id)
    assert content_read == content


def test_must_init():
    storage = PhotoStorage(storage=FileStorage(), imagemagick_convert='')

    with pytest.raises(StorageNotInitializedError):
        storage.count()


def test_photo_storage(s3_storage_db, sample_image):
    storage = PhotoStorage(s3_storage_db, '')

    assert storage.count() == 0

    file_id = storage.store(sample_image, content_type='image/jpeg')
    assert storage.count() == 1
    content_read = storage.get(file_id)
    assert content_read == sample_image

    assert storage.exists(file_id)

    assert storage.get_path(file_id)
    assert storage.get_mimetype(file_id) == 'image/jpeg'

    assert len(list(storage.list())) == 1

    storage.delete(file_id)

    assert repr(storage)


def test_photo_storages_key_access(tmpdir):
    storages = PhotoStorages()

    storages.init_app(names=['db'], storage_directory=str(tmpdir),
                      names_for_s3=[],
                      imagemagick_convert='', access_key_id='', secret_access_key='',
                      region='', bucket='',
                      endpoint_url=None, default_cache_control=None)
    assert storages['db'].count() == 0

    with pytest.raises(PhotoStorageNotFoundError):
        storages['badkey'].count()

    assert 'db' in repr(storages)


def test_clean(file_storage_db, tmpdir):
    storages = PhotoStorages()

    storages.init_app(names=['db'], storage_directory=str(tmpdir),
                      names_for_s3=[],
                      imagemagick_convert='', access_key_id='', secret_access_key='',
                      region='', bucket='',
                      endpoint_url=None, default_cache_control=None)

    content = 'hello world'.encode('utf-8')
    storages['db'].store(content)
    storages.clean()

    assert not os.path.isdir(os.path.join(str(tmpdir), 'db'))


def test_photo_storages_multi(s3_client, s3_bucket, tmpdir):
    storages = PhotoStorages()

    s3_client.create_bucket(Bucket=s3_bucket)

    storages.init_app(names=['db', 'dbs3'], storage_directory=str(tmpdir),
                      names_for_s3=['dbs3'],
                      imagemagick_convert='', access_key_id='', secret_access_key='',
                      region='us-east-1', bucket=s3_bucket,
                      endpoint_url=None, default_cache_control=None)
    assert storages['db'].count() == 0
    assert storages['dbs3'].count() == 0

    assert storages['db'].is_local()
    assert not storages['dbs3'].is_local()

    content = 'hello world'.encode('utf-8')
    storages['dbs3'].store(content)
    assert storages['dbs3'].count() == 1


def test_thumb_missing_convert(s3_storage_db, sample_image):
    storage = PhotoStorage(s3_storage_db, '')

    file_id = storage.store(sample_image, content_type='image/jpeg')

    with pytest.raises(RuntimeError):
        storage.generate_thumbnail(file_id, 'image/jpeg')


def test_thumb_unknown_mime(s3_storage_db, sample_image, convert_path):
    if not convert_path:
        raise pytest.skip('convert utility is not found')

    storage = PhotoStorage(s3_storage_db, convert_path)

    file_id = storage.store(sample_image, content_type='image/jpeg')

    with pytest.raises(RuntimeError):
        storage.generate_thumbnail(file_id, 'image/xxx')


def test_thumb(s3_storage_db, sample_image, convert_path):
    if not convert_path:
        raise pytest.skip('convert utility is not found')

    logging.info("Imagemagick at {} will be invoked".format(convert_path))
    storage = PhotoStorage(s3_storage_db, convert_path)

    file_id = storage.store(sample_image, content_type='image/jpeg')

    thumb_id = storage.generate_thumbnail(file_id, 'image/jpeg')

    assert thumb_id.int != 0

    assert storage.count() == 2

    assert storage.exists(thumb_id)
    assert storage.get_mimetype(thumb_id) == 'image/jpeg'
