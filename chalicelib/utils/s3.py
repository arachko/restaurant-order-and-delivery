import os
import tempfile

from chalicelib.utils.boto_clients import s3_client
from chalicelib.utils.logger import logger


def websites_files_bucket():
    return os.environ["WEBSITES_FILES_BUCKET_NAME"]


def upload_file_to_s3(body, file_path, content_type):
    with tempfile.TemporaryFile() as tf:
        tf.write(body)
        tf.seek(0)
        s3_client.upload_fileobj(tf, websites_files_bucket(), f'{file_path}', ExtraArgs={'ContentType': content_type})
        s3_client.put_object_acl(ACL='public-read', Bucket=websites_files_bucket(), Key=f'{file_path}')
    logger.info(f'upload_file_to_s3:: SUCCESS, file_name_uuid:{file_path} ')
    return file_path


