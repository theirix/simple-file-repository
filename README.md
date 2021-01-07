Simple File Repository
======================

![Build](https://github.com/theirix/simple-file-repository/workflows/build/badge.svg)
![PyPI](https://img.shields.io/pypi/v/simple-file-repository)

A simple file and photo repository.
Underlying storage is a filesystem or a S3-compatible service.

## Installation

    pip install simple_file_repository

## Usage

### File storage

```python
    >>> import uuid
    >>> from simple_file_repository import FileStorage
    >>> storage = FileStorage(storage_directory='/tmp/repo', database='cats')
    >>> storage.store(b'content')
    UUID('72fc4a76-1ab7-4d60-9f6a-94aa0ad45b5b')
    >>> storage.get(uuid.UUID(hex='72fc4a76-1ab7-4d60-9f6a-94aa0ad45b5b'))
    b'content'
    >>> list(storage.list())
    ['72fc4a76-1ab7-4d60-9f6a-94aa0ad45b5b']
```

### Photo storage using S3

```python

from simple_file_repository import PhotoStorages

storages = PhotoStorages()

storages.init_app(names=['cats', 'dogs'],
                  storage_directory='/tmp/repo',
                  names_for_s3=['cats'],
                  imagemagick_convert='/usr/bin/convert',
                  access_key_id='',
                  secret_access_key='',
                  region='us-east-1', bucket='my-s3-bucket')

storages['cats'].store(b'image')

```

## License

MIT