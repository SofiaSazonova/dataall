import logging
import os
from migrations.dataall_migrations.migrationmanager import MigrationManager
from dataall.base.aws.parameter_store import ParameterStoreManager
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

envname = os.environ.get('ENVNAME', 'local')
PARAM_KEY = f'/dataall/{envname}/dataall-migration/revision'


def get_parameter_from_parameter_store():
    try:
        parameter = ParameterStoreManager.get_parameter_value(
            AwsAccountId=os.environ.get('AWS_ACCOUNT_ID'), region=os.environ.get('AWS_REGION'), parameter_path=PARAM_KEY
        )
        return parameter
    except ClientError as e:
        if e.response['Error']['Code'] == 'ParameterNotFound':
            # Handle the case where the parameter is not found
            logger.info(
                f"Error: Parameter '{PARAM_KEY}' not found. Migrations will be executed starting with Initial "
                f'Migration.'
            )
            return None
        # Handle other exceptions
        logger.info(f'Failed to get parameter. Error: {e}')
        return -1
    except Exception as e:
        logger.info(f'Failed to get parameter. Error: {e}')
        return -1


def put_parameter_to_parameter_store(value):
    try:
        ParameterStoreManager.update_parameter(
            AwsAccountId=os.environ.get('AWS_ACCOUNT_ID'),
            region=os.environ.get('AWS_REGION'),
            parameter_name=PARAM_KEY,
            parameter_value=value,
        )
    except Exception as e:
        # Handle other exceptions
        logger.info(f'Failed to put parameter. Error: {e}')


def handler(event, context) -> None:
    revision = get_parameter_from_parameter_store()
    if revision == -1:
        logger.error('Failed to retrieve revision from parameter store')
        return
    manager = MigrationManager()
    upgraded = manager.upgrade(start_key=revision)
    put_parameter_to_parameter_store(manager.current_key)
    if not upgraded:
        logger.error('Failed to upgrade Data.all.')
        raise Exception('Data.all migration failed.')