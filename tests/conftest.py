import os
import shutil

import boto3.resources
import pytest
from moto import mock_s3

from simple_file_repository.filestorage import FileStorage
from simple_file_repository.s3storage import S3Storage


@pytest.fixture
def s3_bucket():
    return 'foobucket'


@pytest.fixture(name='s3_client')
def fixture_s3_client() -> boto3.client:
    # use yielding fixture with context manager, no need to mock_s3 consuming test itself
    # see https://github.com/spulec/moto/issues/620
    with mock_s3():
        client = boto3.client('s3', region_name='us-east-1')
        yield client


# noinspection PyUnusedLocal
@pytest.fixture(name='s3_storage_db')
# pylint: disable=redefined-outer-name
def fixture_s3_storage_db(s3_client, s3_bucket):
    s3_client.create_bucket(Bucket=s3_bucket)

    s3_storage = S3Storage(database='db',
                           bucket=s3_bucket,
                           region='us-east-1',
                           access_key_id='',
                           secret_access_key=''
                           )
    yield s3_storage


@pytest.fixture
def file_storage_db(tmpdir):
    return FileStorage(str(tmpdir), 'db',
                       # use rwxr-x--- permissions
                       file_perm=0o640, dir_perm=0o750)


@pytest.fixture
def sample_image():
    path = os.path.join(os.path.dirname(__file__), 'data', 'test.jpg')
    assert os.path.isfile(path)
    with open(path, 'rb') as f:
        return f.read()


@pytest.fixture
def convert_path():
    return shutil.which('convert')
