import datetime
import logging
from typing import Iterable, Optional
from uuid import UUID, uuid4

import boto3
from botocore.exceptions import IncompleteReadError

from .exceptions import StorageError, StorageNotFoundError
from .storage import Storage


class S3Storage(Storage):
    """S3-based storage"""

    logger = logging.getLogger('S3Storage')

    def __init__(self, database: str, bucket: str,
                 region: str, access_key_id: str, secret_access_key: str,
                 endpoint_url: Optional[str] = None,
                 default_cache_control: Optional[str] = None,
                 config=None):
        """Initialize a photo storages.

         :param database: a database name
         :param bucket: S3 bucket name
         :param region: S3 region name
         :param access_key_id: S3 access key id
         :param secret_access_key: S3 secret access key
         :param endpoint_url: optional URL to S3 endpoint
         :param default_cache_control: optional default cache control for operations.
           It will be passed to `CacheControl` field in S3 calls.
         :param config: a botocore config
         """
        session = boto3.session.Session()
        client_args = dict(service_name='s3', region_name=region,
                           aws_access_key_id=access_key_id,
                           aws_secret_access_key=secret_access_key,
                           config=config)
        if endpoint_url is not None:
            client_args['endpoint_url'] = endpoint_url
        self.s3_client = session.client(**client_args)

        self.bucket = bucket
        self.database = database
        self.default_cache_control = default_cache_control

        if not self.database or not self.database.strip() or '/' in self.database:
            raise ValueError('Invalid database name ' + self.database)

    @staticmethod
    def _generate_file_id():
        file_id = uuid4()
        return file_id

    def _get_key(self, file_id) -> str:
        return self.database + '/' + file_id.hex

    def is_local(self) -> bool:
        return False

    def get(self, file_id: UUID) -> bytes:
        key = self._get_key(file_id)
        try:
            # make retries because botocore does not
            for attempt in range(5):
                try:
                    response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
                    body = response['Body'].read()
                    return body
                except IncompleteReadError as e:
                    self.logger.info("Got IncompleteReadError %s, "
                                     "retry #%d", str(e), attempt)
            raise StorageError("Cannot get file due to IncompleteReadError")
        except self.s3_client.exceptions.NoSuchKey:
            # pylint: disable=raise-missing-from
            raise StorageNotFoundError('File {} does not exist'.format(file_id))
        except self.s3_client.exceptions.ClientError as e:  # pragma: no cover
            raise StorageError(e) from e

    def get_path(self, file_id: UUID, params: Optional[dict] = None) -> str:
        key = self._get_key(file_id)
        expires_sec = int(datetime.timedelta(hours=24).total_seconds())
        effective_params = {'Bucket': self.bucket,
                            'Key': key}
        if params:
            effective_params.update(params)
        url = self.s3_client.generate_presigned_url('get_object',
                                                    Params=effective_params,
                                                    ExpiresIn=expires_sec)
        # self.logger.debug("Presigned url {}".format(url))
        return url

    def exists(self, file_id: UUID) -> bool:
        key = self._get_key(file_id)
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.s3_client.exceptions.ClientError as e:
            # boto3 HEAD will not throw NoSuchKey but a generic 404 error
            if e.response['ResponseMetadata']['HTTPStatusCode'] == 404:
                return False
            raise StorageError(e) from e

    def store(self, content: bytes, content_type: Optional[str] = None,
              tags: Optional[dict] = None, override_id: Optional[UUID] = None,
              cache_control: Optional[str] = None) -> UUID:
        file_id = override_id if override_id else self._generate_file_id()
        key = self._get_key(file_id)
        try:
            client_args = dict(Bucket=self.bucket, Key=key, Body=content)
            if tags:
                tag_str = '&'.join('{}={}'.format(k, v) for k, v in tags.items())
                client_args['Tagging'] = tag_str
            if content_type:
                client_args['ContentType'] = content_type
            if cache_control is not None:
                client_args['CacheControl'] = cache_control
            elif self.default_cache_control is not None:
                client_args['CacheControl'] = self.default_cache_control
            self.s3_client.put_object(**client_args)
            return file_id
        except self.s3_client.exceptions.ClientError as e:  # pragma: no cover
            raise StorageError(e) from e

    def delete(self, file_id: UUID):
        key = self._get_key(file_id)
        # must throw an error if no key found
        if not self.exists(file_id):
            raise StorageNotFoundError('File {} does not exist'.format(file_id))
        # now delete (will not throw error if no such key)
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
        except self.s3_client.exceptions.ClientError as e:  # pragma: no cover
            raise StorageError(e) from e

    def get_mimetype(self, file_id: UUID) -> str:
        key = self._get_key(file_id)
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=key)
            content_type = response.get('ContentType', None)
            if content_type is None:
                content_type = 'application/octet-stream'
            return content_type
        except self.s3_client.exceptions.ClientError as e:  # pragma: no cover
            raise StorageError(e) from e

    def count(self) -> int:
        paginator = self.s3_client.get_paginator("list_objects_v2")
        keys_count = sum((page['KeyCount'] for page in
                          paginator.paginate(Bucket=self.bucket, Prefix=self.database)))
        return keys_count

    def list(self) -> Iterable[str]:
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.database):
            yield from (content['Key'].split('/')[-1] for content in page.get('Contents', []))

    def clean(self):
        # Do not ever try to clean bucket
        pass

    def __repr__(self) -> str:
        return "S3Storage db={}".format(self.database)
