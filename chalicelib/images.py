import cgi
import copy
import os
from io import BytesIO
from typing import Tuple

from chalice import Response

from chalicelib.constants.constants import MAIN_IMAGE_NAME, THUMB_IMAGE_NAME
from chalicelib.constants.status_codes import http200
from chalicelib.utils import auth as utils_auth, app as utils_app
from chalicelib.utils.s3 import upload_file_to_s3
from PIL import Image

entities_to_upload_attachment_white_list = ['restaurant', 'menu_item']


def get_resize_width_height(image: Image, max_width: int) -> Tuple[int, int]:
    width, height = image.size
    divider = max([width, height]) / max_width
    return int(width / divider), int(height / divider)


def get_thumbnail(image: Image) -> Image:
    image_thumb = copy.deepcopy(image)
    width, height = get_resize_width_height(image_thumb, int(os.environ.get('MAX_THUMBNAIL_WIDTH')))
    image_thumb.thumbnail(size=(width, height))
    return image_thumb


def compress_images(image_file_obj: BytesIO) -> Tuple[bytes, bytes]:
    image: Image = Image.open(image_file_obj)
    image = image.resize(size=get_resize_width_height(image, int(os.environ.get('MAX_IMG_WIDTH'))))

    image_thumb: Image = get_thumbnail(image)

    buf_thumb = BytesIO()
    image.save(buf_thumb, format='JPEG', optimize=True, quality=100)

    buf_orig = BytesIO()
    image_thumb.save(buf_orig, format='JPEG', optimize=True, quality=100)

    return buf_thumb.getvalue(), buf_orig.getvalue()


def parse_multipart_request_data(current_request):
    content_type, boundary_dict = cgi.parse_header(current_request.headers['content-type'])
    boundary_dict['boundary'] = boundary_dict['boundary'].encode("utf-8")
    body = cgi.parse_multipart(BytesIO(current_request.raw_body), boundary_dict)
    entity_type = body['entityType'][0]
    restaurant_id = body['restaurantId'][0]
    menu_item_id = body.get('menuItemId', [None])[0]
    file_content = body['fileContent'][0]
    return file_content, entity_type, menu_item_id, restaurant_id


@utils_app.request_exception_handler
@utils_auth.authenticate
def image_upload(current_request) -> Response:
    company_id = current_request.auth_result['company_id']
    file_content, entity_type, menu_item_id, restaurant_id = parse_multipart_request_data(current_request)

    content_main, content_thumb = compress_images(BytesIO(file_content))

    restaurant_path = f'{company_id}/{restaurant_id}/images'
    menu_item_path = f'{company_id}/{restaurant_id}/{menu_item_id}/images'

    if entity_type == 'restaurant':
        path_main, path_thumb = f'{restaurant_path}/{MAIN_IMAGE_NAME}', f'{restaurant_path}/{THUMB_IMAGE_NAME}'
    elif entity_type == 'menu_item':
        path_main, path_thumb = f'{menu_item_path}/{MAIN_IMAGE_NAME}', f'{menu_item_path}/{THUMB_IMAGE_NAME}'
    else:
        raise Exception(f'You could not upload attachment to {entity_type=}')

    upload_file_to_s3(content_main, path_main, 'application/octet-stream')
    upload_file_to_s3(content_thumb, path_thumb, 'application/octet-stream')
    return Response(status_code=http200, headers={"Content-Type": 'application/json'},
                    body={'message': f'{entity_type} image was updated successfully'})
