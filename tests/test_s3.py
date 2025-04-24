import logging
import time
import uuid

import pytest
import requests

from simple_file_repository.exceptions import StorageError
from simple_file_repository.s3storage import S3Storage


def test_moto_works(s3_client, s3_bucket):
    s3_client.create_bucket(Bucket=s3_bucket)

    s3_storage = S3Storage(database='db', bucket=s3_bucket,
                           region='us-east-1',
                           access_key_id='', secret_access_key='')
    assert s3_storage.count() == 0
    file_id = s3_storage.store(b'data')
    assert file_id


def test_moto_nosuchkey(s3_client):
    s3_client.create_bucket(Bucket='mybucket')

    # it does not throw s3_client.exceptions.ClientError:
    try:
        s3_client.get_object(Bucket='mybucket', Key='badkey')
    except s3_client.exceptions.NoSuchKey as e:
        logging.debug("Error: %r", e)
        assert e.response['Error']['Code'] == 'NoSuchKey'


def test_moto_delete_nonexistent(s3_client):
    s3_client.create_bucket(Bucket='mybucket')

    # it does not throw at all
    s3_client.delete_object(Bucket='mybucket', Key='badkey')


def test_s3_storage_works(s3_storage_db):
    file_id = s3_storage_db.store(b'data')
    assert file_id
    assert s3_storage_db.count() == 1


def test_empty_file_storage(s3_storage_db):
    assert s3_storage_db.count() == 0


def test_write(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    file_id = s3_storage_db.store(content)
    assert file_id.int != 0
    assert s3_storage_db.count() == 1
    content_read = s3_storage_db.get(file_id)
    assert content_read == content


def test_write_with_content_type(s3_storage_db, sample_image, s3_client, s3_bucket):
    # set obscure content type
    content_type = 'application/pdf'
    file_id = s3_storage_db.store(sample_image, content_type=content_type, tags=None)
    assert s3_storage_db.count() == 1

    response = s3_client.get_object(Bucket=s3_bucket, Key='db' + '/' + file_id.hex)
    assert response['ContentType'] == content_type

    # check content-type in requested presigned url - it is overridden
    path = s3_storage_db.get_path(file_id)
    r = requests.get(path, timeout=30)
    assert r.status_code == 200
    logging.debug(r.headers)
    assert r.headers['Content-Type'] == content_type
    assert 'Cache-Control' not in r.headers


def test_write_with_cache_control(s3_storage_db, sample_image, s3_client, s3_bucket):
    # set obscure content type
    cache_control = 'public'
    file_id = s3_storage_db.store(sample_image, cache_control=cache_control)
    assert s3_storage_db.count() == 1

    response = s3_client.get_object(Bucket=s3_bucket, Key='db' + '/' + file_id.hex)
    assert response['CacheControl'] == cache_control

    path = s3_storage_db.get_path(file_id)
    r = requests.get(path, timeout=30)
    assert r.status_code == 200
    logging.debug(r.headers)
    assert 'Cache-Control' in r.headers
    assert r.headers['Cache-Control'] == cache_control


def test_write_with_default_cache_control(sample_image, s3_client, s3_bucket):
    cache_control = 'public'

    # create manually
    s3_client.create_bucket(Bucket=s3_bucket)

    s3_storage_db = S3Storage(database='db',
                              bucket=s3_bucket,
                              region='us-east-1',
                              access_key_id='',
                              secret_access_key='',
                              # set obscure content type
                              default_cache_control=cache_control
                              )

    file_id = s3_storage_db.store(sample_image)
    assert s3_storage_db.count() == 1

    path = s3_storage_db.get_path(file_id)
    r = requests.get(path, timeout=30)
    assert r.status_code == 200
    logging.debug(r.headers)
    assert 'Cache-Control' in r.headers
    assert r.headers['Cache-Control'] == cache_control


def test_tags(s3_storage_db, sample_image, s3_client, s3_bucket):
    file_id = s3_storage_db.store(sample_image, content_type='image/jpeg',
                                  tags=dict(MyTag='MyValue', SecondTag='SecondValue'))

    response = s3_client.get_object_tagging(Bucket=s3_bucket, Key='db' + '/' + file_id.hex)
    assert len(response['TagSet']) == 2
    assert dict(Key='MyTag', Value='MyValue') in response['TagSet']
    assert dict(Key='SecondTag', Value='SecondValue') in response['TagSet']


def test_read_bad(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    file_id = s3_storage_db.store(content)
    assert s3_storage_db.count() == 1
    wrong_id = uuid.UUID(hex=file_id.hex[::-1])
    with pytest.raises(StorageError):
        s3_storage_db.get(wrong_id)


def test_exists(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    file_id = s3_storage_db.store(content)
    assert s3_storage_db.exists(file_id)
    wrong_id = uuid.UUID(hex=file_id.hex[::-1])
    assert not s3_storage_db.exists(wrong_id)


def test_get_mimetype(s3_storage_db, sample_image):
    file_id = s3_storage_db.store(sample_image, content_type='image/jpeg')
    mimetype = s3_storage_db.get_mimetype(file_id)
    assert mimetype == 'image/jpeg'


def test_get_mimetype_plain(s3_storage_db):
    file_id = s3_storage_db.store(b'cafe\x01D\04')
    mimetype = s3_storage_db.get_mimetype(file_id)
    assert mimetype == 'binary/octet-stream'


def test_get_mimetype_explicit_needed(s3_storage_db, sample_image):
    file_id = s3_storage_db.store(sample_image)
    mimetype = s3_storage_db.get_mimetype(file_id)
    assert mimetype != 'image/jpeg'


def test_write_no_dedup(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    file_id1 = s3_storage_db.store(content)
    assert s3_storage_db.count() == 1
    file_id2 = s3_storage_db.store(content)
    assert s3_storage_db.count() == 2
    assert file_id1 != file_id2


def test_write_override(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    override_id = uuid.UUID(hex='4c23d90e-7cf9-11ea-80c9-784f43528e33')
    file_id = s3_storage_db.store(content, override_id=override_id)
    assert file_id == override_id
    assert s3_storage_db.count() == 1
    assert s3_storage_db.exists(override_id)


def test_read_path(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    file_id = s3_storage_db.store(content)
    path = s3_storage_db.get_path(file_id)
    assert path
    assert path.startswith('https://')

    r = requests.get(path, timeout=30)
    assert r.status_code == 200
    fetched_content = r.content
    logging.debug(fetched_content)
    assert fetched_content == content


def test_presigned_performance(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    file_id = s3_storage_db.store(content)
    start_time = time.perf_counter()
    count = 1000
    for _ in range(count):
        s3_storage_db.get_path(file_id)
    sec_per_req = (time.perf_counter() - start_time) / count
    logging.info("Time per url: {:2f} ms".format(sec_per_req * 1000))
    # usually it is about 1 ms. test if it is less than 100 ms
    assert sec_per_req < 0.100


def test_clean(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    s3_storage_db.store(content)
    assert s3_storage_db.count() == 1
    s3_storage_db.clean()
    # nothing changed
    assert s3_storage_db.count() == 1


def test_delete_existing(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    file_id = s3_storage_db.store(content)
    assert s3_storage_db.count() == 1
    s3_storage_db.delete(file_id)
    assert s3_storage_db.count() == 0


def test_delete_nonexisting(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    file_id = s3_storage_db.store(content)
    assert s3_storage_db.count() == 1
    wrong_id = uuid.UUID(hex=file_id.hex[::-1])
    with pytest.raises(StorageError):
        s3_storage_db.delete(wrong_id)
    assert s3_storage_db.count() == 1


def test_list(s3_storage_db):
    file_id1 = s3_storage_db.store(b'foo')
    file_id2 = s3_storage_db.store(b'bar')
    listed = list(s3_storage_db.list())
    assert len(listed) == 2
    assert file_id1.hex in listed
    assert file_id2.hex in listed


def test_repr(s3_storage_db):
    assert repr(s3_storage_db) == 'S3Storage db=db'
    assert not s3_storage_db.is_local()


def test_clean_ignored(s3_storage_db):
    content = 'hello world'.encode('utf-8')
    s3_storage_db.store(content)
    assert s3_storage_db.count() == 1
    s3_storage_db.clean()
    assert s3_storage_db.count() == 1
