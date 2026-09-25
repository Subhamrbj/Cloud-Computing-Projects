from pathlib import Path
import boto3
from .config import settings

class LocalStorage:
    def __init__(self,root): self.root=Path(root).resolve()
    def _path(self,key):
        path=(self.root/key).resolve()
        if not path.is_relative_to(self.root): raise ValueError('Unsafe storage key')
        return path
    def put(self,key,content,content_type='application/octet-stream'):
        path=self._path(key); path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(content)
    def get(self,key): return self._path(key).read_bytes()
    def delete(self,key): self._path(key).unlink(missing_ok=True)
    def health(self): self.root.mkdir(parents=True,exist_ok=True); return True

class S3Storage:
    def __init__(self):
        self.client=boto3.client('s3',region_name=settings.s3_region,endpoint_url=settings.s3_endpoint_url or None)
        self.bucket=settings.s3_bucket
    def put(self,key,content,content_type='application/octet-stream'):
        self.client.put_object(Bucket=self.bucket,Key=key,Body=content,ContentType=content_type)
    def get(self,key): return self.client.get_object(Bucket=self.bucket,Key=key)['Body'].read()
    def delete(self,key): self.client.delete_object(Bucket=self.bucket,Key=key)
    def health(self): self.client.head_bucket(Bucket=self.bucket); return True

storage = S3Storage() if settings.storage_backend=='s3' else LocalStorage(settings.storage_dir)
