import logging

import pytest

from integration_tests.client import GqlError
from integration_tests.core.environment.queries import (
    create_environment,
    get_environment,
    delete_environment,
    list_environments,
)
from integration_tests.core.organizations.queries import create_organization
from integration_tests.core.stack.utils import check_stack_ready

log = logging.getLogger(__name__)


def create_env(client, group, org_uri, account_id, region, tags=[]):
    env = create_environment(
        client, name='testEnvA', group=group, organizationUri=org_uri, awsAccountId=account_id, region=region, tags=tags
    )
    check_stack_ready(client, env.environmentUri, env.stack.stackUri)
    return get_environment(client, env.environmentUri)


def delete_env(client, env):
    check_stack_ready(client, env.environmentUri, env.stack.stackUri)
    try:
        return delete_environment(client, env.environmentUri)
    except GqlError:
        log.exception('unexpected error when deleting environment')
        return False


"""
Session envs persist accross the duration of the whole integ test suite and are meant to make the test suite run faster (env creation takes ~2 mins).
For this reason they must stay immutable as changes to them will affect the rest of the tests.
"""


@pytest.fixture(scope='session')
def session_env1(client1, group1, org1, session_id, testdata):
    envdata = testdata.envs['session_env1']
    env = None
    try:
        env = create_env(client1, group1, org1['organizationUri'], envdata.accountId, envdata.region, tags=[session_id])
        yield env
    finally:
        if env:
            delete_env(client1, env)


@pytest.fixture(scope='session')
def session_env2(client1, group1, org1, session_id, testdata):
    envdata = testdata.envs['session_env2']
    env = None
    try:
        env = create_env(client1, group1, org1['organizationUri'], envdata.accountId, envdata.region, tags=[session_id])
        yield env
    finally:
        if env:
            delete_env(client1, env)


"""
Temp envs will be created and deleted per test, use with caution as they might increase the runtime of the test suite.
They are suitable to test env mutations.
"""


@pytest.fixture(scope='function')
def temp_env1(client1, group1, org1, testdata):
    envdata = testdata.envs['temp_env1']
    env = None
    try:
        env = create_env(client1, group1, org1['organizationUri'], envdata.accountId, envdata.region)
        yield env
    finally:
        if env:
            delete_env(client1, env)


"""
Persistent environments must always be present (if not i.e first run they will be created but won't be removed).
They are suitable for testing backwards compatibility. 
"""


def get_or_create_persistent_env(env_name, client, group, testdata):
    envs = list_environments(client, term=env_name).nodes
    if envs:
        return envs[0]
    else:
        envdata = testdata.envs[env_name]
        org = create_organization(client, f'org_{env_name}', group)
        env = create_env(client, group, org['organizationUri'], envdata.accountId, envdata.region, tags=[env_name])
        if env.stack.status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
            return env
        else:
            delete_env(client, env['environmentUri'])
            raise RuntimeError(f'failed to create {env_name=} {env=}')


@pytest.fixture(scope='session')
def persistent_env1(client1, group1, testdata):
    return get_or_create_persistent_env('persistent_env1', client1, group1, testdata)
