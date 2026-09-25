import os
from pathlib import Path
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv('DATABASE_URL', 'sqlite:///./diet_planner.db')
    secret_key: str = os.getenv('SECRET_KEY', 'development-only-change-before-deploy')
    storage_backend: str = os.getenv('STORAGE_BACKEND', 'local')
    storage_dir: str = os.getenv('STORAGE_DIR', './data/objects')
    s3_bucket: str = os.getenv('S3_BUCKET', '')
    s3_endpoint_url: str = os.getenv('S3_ENDPOINT_URL', '')
    s3_region: str = os.getenv('S3_REGION', 'us-east-1')
    ai_api_url: str = os.getenv('AI_API_URL', '')
    ai_api_key: str = os.getenv('AI_API_KEY', '')
    ai_model: str = os.getenv('AI_MODEL', 'gpt-4o-mini')
    cors_origins: str = os.getenv('CORS_ORIGINS', 'http://localhost:5173')
    max_upload_bytes: int = int(os.getenv('MAX_UPLOAD_BYTES', str(5 * 1024 * 1024)))

    def validate(self):
        if os.getenv('APP_ENV') == 'production' and (self.secret_key == 'development-only-change-before-deploy' or len(self.secret_key) < 32):
            raise RuntimeError('Set a random SECRET_KEY of at least 32 characters in production')
        if self.storage_backend not in ('local', 's3'):
            raise RuntimeError('STORAGE_BACKEND must be local or s3')
        if self.storage_backend == 's3' and not self.s3_bucket:
            raise RuntimeError('S3_BUCKET is required for S3 storage')

settings = Settings()
settings.validate()
