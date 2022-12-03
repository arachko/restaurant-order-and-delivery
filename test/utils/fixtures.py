import os

import pytest
from chalice.local import LocalGateway
from chalice.cli import factory

from chalicelib.utils.logger import log_message


def local_gateway() -> LocalGateway:
    config = factory.CLIFactory(
        project_dir='..', environ=os.environ).create_config_obj(chalice_stage_name=os.environ.get('stage', 'test'))
    log_message(f'local_gateway os.environ = {os.environ.get("stage", "test")}')
    return LocalGateway(config.chalice_app, config)


@pytest.fixture(scope='session')
def chalice_gateway() -> LocalGateway:
    yield local_gateway()
