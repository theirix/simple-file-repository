import os
import shutil
import uuid

import pytest

from simple_file_repository.exceptions import (
    StorageError,
    StorageNotFoundError,
    StorageNotInitializedError,
)
from simple_file_repository.filestorage import FileStorage


def test_create_dir(tmpdir):
    file_storage_db = FileStorage(str(tmpdir), "db")
    assert os.path.isdir(os.path.join(str(tmpdir), "db"))
    assert file_storage_db.count() == 0


def test_empty_file_storage(file_storage_db, tmpdir):
    assert file_storage_db.count() == 0
    assert os.path.isdir(os.path.join(str(tmpdir), "db"))


def test_write(file_storage_db):
    content = "hello world".encode("utf-8")
    file_id = file_storage_db.store(content)
    assert file_id.int != 0
    assert file_storage_db.count() == 1
    content_read = file_storage_db.get(file_id)
    assert content_read == content


def test_read_bad(file_storage_db):
    content = "hello world".encode("utf-8")
    file_id = file_storage_db.store(content)
    assert file_storage_db.count() == 1
    wrong_id = uuid.UUID(hex=file_id.hex[::-1])
    with pytest.raises(StorageError):
        file_storage_db.get(wrong_id)


def test_write_no_dedup(file_storage_db):
    content = "hello world".encode("utf-8")
    file_id1 = file_storage_db.store(content)
    assert file_storage_db.count() == 1
    file_id2 = file_storage_db.store(content)
    assert file_storage_db.count() == 2
    assert file_id1 != file_id2


def test_read_path(file_storage_db):
    content = "hello world".encode("utf-8")
    file_id = file_storage_db.store(content)
    assert file_storage_db.count() == 1
    file_path = file_storage_db.get_path(file_id)
    assert file_path
    assert os.path.isfile(file_path)


def test_delete_existing(file_storage_db):
    content = "hello world".encode("utf-8")
    file_id = file_storage_db.store(content)
    assert file_storage_db.count() == 1
    file_storage_db.delete(file_id)
    assert file_storage_db.count() == 0


def test_delete_nonexisting(file_storage_db):
    content = "hello world".encode("utf-8")
    file_id = file_storage_db.store(content)
    assert file_storage_db.count() == 1
    wrong_id = uuid.UUID(hex=file_id.hex[::-1])
    with pytest.raises(StorageError):
        file_storage_db.delete(wrong_id)
    assert file_storage_db.count() == 1


def test_delete_nonexisting_silent(file_storage_db):
    content = "hello world".encode("utf-8")
    file_id = file_storage_db.store(content)
    assert file_storage_db.count() == 1
    wrong_id = uuid.UUID(hex=file_id.hex[::-1])
    file_storage_db.delete(wrong_id, silent=True)
    assert file_storage_db.count() == 1


def test_list(file_storage_db):
    file_id1 = file_storage_db.store(b"foo")
    file_id2 = file_storage_db.store(b"bar")
    listed = list(file_storage_db.list())
    assert len(listed) == 2
    assert file_id1.hex in listed
    assert file_id2.hex in listed


def test_exists(file_storage_db):
    content = "hello world".encode("utf-8")
    file_id = file_storage_db.store(content)
    assert file_storage_db.exists(file_id)
    assert not file_storage_db.exists(uuid.uuid4())


def test_repr(file_storage_db):
    assert repr(file_storage_db) == "FileStorage db=db"
    assert file_storage_db.is_local()


def test_get_mimetype(file_storage_db, sample_image):
    file_id = file_storage_db.store(sample_image)
    mimetype = file_storage_db.get_mimetype(file_id)
    assert mimetype == "image/jpeg"


def test_get_mimetype_plain(file_storage_db):
    file_id = file_storage_db.store(b"cafe\x01D\04")
    mimetype = file_storage_db.get_mimetype(file_id)
    assert mimetype == "application/octet-stream"


def test_clean(file_storage_db, tmpdir):
    content = "hello world".encode("utf-8")
    file_storage_db.store(content)
    assert file_storage_db.count() == 1
    file_storage_db.clean()
    assert not os.path.isdir(os.path.join(str(tmpdir), "db"))


def test_access_after_clean(file_storage_db):
    content = "hello world".encode("utf-8")
    file_storage_db.store(content)
    assert file_storage_db.count() == 1
    file_storage_db.clean()
    with pytest.raises(StorageError):
        file_storage_db.store(content)


def test_missing_dir(file_storage_db, tmpdir):
    content = "hello world".encode("utf-8")
    file_id = file_storage_db.store(content)
    shutil.rmtree(os.path.join(str(tmpdir), "db"))
    with pytest.raises(StorageNotFoundError):
        file_storage_db.get(file_id)
    with pytest.raises(StorageNotFoundError):
        file_storage_db.get_path(file_id)
    with pytest.raises(StorageNotFoundError):
        file_storage_db.get_mimetype(file_id)

    with pytest.raises(StorageNotInitializedError):
        file_storage_db.store(content)
    with pytest.raises(StorageNotInitializedError):
        assert file_storage_db.count() == 0
    with pytest.raises(StorageNotInitializedError):
        file_storage_db.list()
