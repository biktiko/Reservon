import logging
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)

class MediaStorage(S3Boto3Storage):
    file_overwrite = False

    def save(self, name, content, max_length=None):
        logger.info(f"MediaStorage.save() name={name}")
        return super().save(name, content, max_length=max_length)
