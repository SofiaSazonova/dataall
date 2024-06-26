from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService
from dataall.base.db import exceptions
from dataall.modules.shares_base.db.share_object_models import ShareObject
from dataall.modules.s3_datasets_shares.db.s3_share_object_repositories import S3ShareObjectRepository
from dataall.modules.shares_base.services.share_permissions import SHARE_OBJECT_APPROVER
from dataall.modules.s3_datasets.services.dataset_permissions import (
    DELETE_DATASET,
    DELETE_DATASET_TABLE,
    DELETE_DATASET_FOLDER,
)
from dataall.modules.datasets_base.services.datasets_enums import DatasetRole, DatasetTypes
from dataall.modules.datasets_base.services.dataset_service_interface import DatasetServiceInterface


import logging

log = logging.getLogger(__name__)


class S3ShareDatasetService(DatasetServiceInterface):
    @property
    def dataset_type(self):
        return DatasetTypes.S3

    @staticmethod
    def resolve_additional_dataset_user_role(session, uri, username, groups):
        """Implemented as part of the DatasetServiceInterface"""
        share = S3ShareObjectRepository.get_share_by_dataset_attributes(session, uri, username, groups)
        if share is not None:
            return DatasetRole.Shared.value
        return None

    @staticmethod
    def check_before_delete(session, uri, **kwargs):
        """Implemented as part of the DatasetServiceInterface"""
        action = kwargs.get('action')
        if action in [DELETE_DATASET_FOLDER, DELETE_DATASET_TABLE]:
            existing_s3_shared_items = S3ShareObjectRepository.check_existing_s3_shared_items(session, uri)
            if existing_s3_shared_items:
                raise exceptions.ResourceShared(
                    action=action,
                    message='Revoke all shares for this item before deletion',
                )
        elif action in [DELETE_DATASET]:
            shares = S3ShareObjectRepository.list_s3_dataset_shares_with_existing_shared_items(
                session=session, dataset_uri=uri
            )
            if shares:
                raise exceptions.ResourceShared(
                    action=DELETE_DATASET,
                    message='Revoke all dataset shares before deletion.',
                )
        else:
            raise exceptions.RequiredParameter('Delete action')
        return True

    @staticmethod
    def execute_on_delete(session, uri, **kwargs):
        """Implemented as part of the DatasetServiceInterface"""
        action = kwargs.get('action')
        if action in [DELETE_DATASET_FOLDER, DELETE_DATASET_TABLE]:
            S3ShareObjectRepository.delete_s3_share_item(session, uri)
        elif action in [DELETE_DATASET]:
            S3ShareObjectRepository.delete_s3_shares_with_no_shared_items(session, uri)
        else:
            raise exceptions.RequiredParameter('Delete action')
        return True

    @staticmethod
    def append_to_list_user_datasets(session, username, groups):
        """Implemented as part of the DatasetServiceInterface"""
        return S3ShareObjectRepository.list_user_s3_shared_datasets(session, username, groups)

    @staticmethod
    def extend_attach_steward_permissions(session, dataset, new_stewards, **kwargs):
        """Implemented as part of the DatasetServiceInterface"""
        dataset_shares = S3ShareObjectRepository.find_s3_dataset_shares(session, dataset.datasetUri)
        if dataset_shares:
            for share in dataset_shares:
                ResourcePolicyService.attach_resource_policy(
                    session=session,
                    group=new_stewards,
                    permissions=SHARE_OBJECT_APPROVER,
                    resource_uri=share.shareUri,
                    resource_type=ShareObject.__name__,
                )
                if dataset.stewards != dataset.SamlAdminGroupName:
                    ResourcePolicyService.delete_resource_policy(
                        session=session,
                        group=dataset.stewards,
                        resource_uri=share.shareUri,
                    )

    @staticmethod
    def extend_delete_steward_permissions(session, dataset, **kwargs):
        """Implemented as part of the DatasetServiceInterface"""
        dataset_shares = S3ShareObjectRepository.find_s3_dataset_shares(session, dataset.datasetUri)
        if dataset_shares:
            for share in dataset_shares:
                if dataset.stewards != dataset.SamlAdminGroupName:
                    ResourcePolicyService.delete_resource_policy(
                        session=session,
                        group=dataset.stewards,
                        resource_uri=share.shareUri,
                    )
