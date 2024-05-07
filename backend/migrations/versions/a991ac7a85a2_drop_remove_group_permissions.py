"""drop_remove_group_permissions

Revision ID: a991ac7a85a2
Revises: c6d01930179d
Create Date: 2024-05-02 15:23:01.516657

"""

from sqlalchemy import and_
from dataall.core.permissions.services.environment_permissions import REMOVE_ENVIRONMENT_GROUP
from dataall.core.permissions.db.resource_policy.resource_policy_models import ResourcePolicy
from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService
from alembic import op
from sqlalchemy import orm
from dataall.core.environment.db.environment_models import Environment

# revision identifiers, used by Alembic.
revision = 'a991ac7a85a2'
down_revision = 'c6d01930179d'
branch_labels = None
depends_on = None


def get_session():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    return session


def upgrade():
    session = get_session()
    environments = session.query(Environment).all()
    for env in environments:
        admin_group = env.SamlGroupName
        suspicious_permissions_principals = (
            session.query(ResourcePolicy.principalId)
            .filter(
                and_(
                    ResourcePolicy.principalType == 'GROUP',
                    ResourcePolicy.principalId != admin_group,
                    ResourcePolicy.resourceType == Environment.__name__,
                    ResourcePolicy.resourceUri == env.environmentUri,
                )
            )
            .all()
        )
        for group in suspicious_permissions_principals:
            permissions = ResourcePolicyService.get_resource_policy_permissions(session, group, env.environmentUri)
            permissions = [permission.name for permission in permissions if permission.name != REMOVE_ENVIRONMENT_GROUP]
            ResourcePolicyService.update_resource_policy(
                session,
                resource_uri=env.environmentUri,
                resource_type=Environment.__name__,
                old_group=group,
                new_group=group,
                new_permissions=permissions,
            )


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    print('Skipping ... ')
    # ### end Alembic commands ###