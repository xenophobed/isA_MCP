"""
Mock for MinIO/S3 client.

Provides a mock implementation of MinIO client
for testing file storage operations without a real MinIO instance.
"""
from typing import Any, Dict, List, Optional, BinaryIO, Iterator
from dataclasses import dataclass, field
from datetime import datetime
import io
import hashlib


@dataclass
class MockObject:
    """Represents a stored object."""
    bucket_name: str
    object_name: str
    data: bytes
    content_type: str = "application/octet-stream"
    metadata: Dict[str, str] = field(default_factory=dict)
    etag: str = ""
    size: int = 0
    last_modified: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        self.size = len(self.data)
        self.etag = hashlib.md5(self.data).hexdigest()


@dataclass
class MockBucket:
    """Represents a storage bucket."""
    name: str
    creation_date: datetime = field(default_factory=datetime.utcnow)


class MockMinioClient:
    """
    Mock for MinIO/S3 client.

    Provides in-memory storage for testing file operations.

    Example usage:
        client = MockMinioClient()
        client.make_bucket("test-bucket")
        client.put_object("test-bucket", "file.txt", io.BytesIO(b"Hello"), 5)
        data = client.get_object("test-bucket", "file.txt")
    """

    def __init__(self):
        self.buckets: Dict[str, MockBucket] = {}
        self.objects: Dict[str, Dict[str, MockObject]] = {}

    def make_bucket(self, bucket_name: str, **kwargs) -> None:
        """Create a new bucket."""
        if bucket_name in self.buckets:
            raise ValueError(f"Bucket {bucket_name} already exists")

        self.buckets[bucket_name] = MockBucket(name=bucket_name)
        self.objects[bucket_name] = {}

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists."""
        return bucket_name in self.buckets

    def remove_bucket(self, bucket_name: str) -> None:
        """Remove a bucket."""
        if bucket_name not in self.buckets:
            raise ValueError(f"Bucket {bucket_name} not found")

        if self.objects.get(bucket_name):
            raise ValueError(f"Bucket {bucket_name} is not empty")

        del self.buckets[bucket_name]
        del self.objects[bucket_name]

    def list_buckets(self) -> List[MockBucket]:
        """List all buckets."""
        return list(self.buckets.values())

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: int = -1,
        content_type: str = "application/octet-stream",
        metadata: Dict[str, str] = None,
        **kwargs
    ) -> MockObject:
        """Upload an object."""
        if bucket_name not in self.buckets:
            raise ValueError(f"Bucket {bucket_name} not found")

        # Read all data
        if hasattr(data, 'read'):
            content = data.read()
        else:
            content = data

        obj = MockObject(
            bucket_name=bucket_name,
            object_name=object_name,
            data=content,
            content_type=content_type,
            metadata=metadata or {}
        )

        self.objects[bucket_name][object_name] = obj
        return obj

    def get_object(
        self,
        bucket_name: str,
        object_name: str,
        **kwargs
    ) -> "MockResponse":
        """Get an object."""
        if bucket_name not in self.buckets:
            raise ValueError(f"Bucket {bucket_name} not found")

        if object_name not in self.objects.get(bucket_name, {}):
            raise ValueError(f"Object {object_name} not found")

        obj = self.objects[bucket_name][object_name]
        return MockResponse(obj.data)

    def fget_object(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        **kwargs
    ) -> MockObject:
        """Download object to file."""
        if bucket_name not in self.buckets:
            raise ValueError(f"Bucket {bucket_name} not found")

        if object_name not in self.objects.get(bucket_name, {}):
            raise ValueError(f"Object {object_name} not found")

        obj = self.objects[bucket_name][object_name]

        with open(file_path, 'wb') as f:
            f.write(obj.data)

        return obj

    def fput_object(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
        metadata: Dict[str, str] = None,
        **kwargs
    ) -> MockObject:
        """Upload file to object."""
        with open(file_path, 'rb') as f:
            data = f.read()

        return self.put_object(
            bucket_name,
            object_name,
            io.BytesIO(data),
            len(data),
            content_type,
            metadata
        )

    def remove_object(self, bucket_name: str, object_name: str) -> None:
        """Remove an object."""
        if bucket_name not in self.buckets:
            raise ValueError(f"Bucket {bucket_name} not found")

        if object_name in self.objects.get(bucket_name, {}):
            del self.objects[bucket_name][object_name]

    def list_objects(
        self,
        bucket_name: str,
        prefix: str = "",
        recursive: bool = False,
        **kwargs
    ) -> Iterator[MockObject]:
        """List objects in bucket."""
        if bucket_name not in self.buckets:
            raise ValueError(f"Bucket {bucket_name} not found")

        for name, obj in self.objects.get(bucket_name, {}).items():
            if name.startswith(prefix):
                yield obj

    def stat_object(
        self,
        bucket_name: str,
        object_name: str,
        **kwargs
    ) -> MockObject:
        """Get object metadata."""
        if bucket_name not in self.buckets:
            raise ValueError(f"Bucket {bucket_name} not found")

        if object_name not in self.objects.get(bucket_name, {}):
            raise ValueError(f"Object {object_name} not found")

        return self.objects[bucket_name][object_name]

    def copy_object(
        self,
        bucket_name: str,
        object_name: str,
        source: str,
        **kwargs
    ) -> MockObject:
        """Copy an object."""
        # Parse source (format: bucket/object)
        parts = source.split("/", 1)
        src_bucket = parts[0]
        src_object = parts[1] if len(parts) > 1 else ""

        if src_bucket not in self.buckets:
            raise ValueError(f"Source bucket {src_bucket} not found")

        if src_object not in self.objects.get(src_bucket, {}):
            raise ValueError(f"Source object {src_object} not found")

        src_obj = self.objects[src_bucket][src_object]

        return self.put_object(
            bucket_name,
            object_name,
            io.BytesIO(src_obj.data),
            src_obj.size,
            src_obj.content_type,
            src_obj.metadata.copy()
        )

    def presigned_get_object(
        self,
        bucket_name: str,
        object_name: str,
        expires: int = 604800,
        **kwargs
    ) -> str:
        """Generate presigned URL for GET."""
        return f"http://mock-minio/{bucket_name}/{object_name}?expires={expires}"

    def presigned_put_object(
        self,
        bucket_name: str,
        object_name: str,
        expires: int = 604800,
        **kwargs
    ) -> str:
        """Generate presigned URL for PUT."""
        return f"http://mock-minio/{bucket_name}/{object_name}?expires={expires}&method=PUT"


class MockResponse:
    """Mock response object for get_object."""

    def __init__(self, data: bytes):
        self._data = data
        self._stream = io.BytesIO(data)

    def read(self, size: int = -1) -> bytes:
        """Read data."""
        return self._stream.read(size)

    def close(self) -> None:
        """Close the response."""
        self._stream.close()

    def release_conn(self) -> None:
        """Release connection."""
        pass

    @property
    def data(self) -> bytes:
        """Get all data."""
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
