import logging
import enum
import os

from dataall.base.config import config
from dataall.core.tasks.db.task_models import Task
from dataall.core.tasks.service_handlers import Worker
from dataall.modules.shares_base.db.share_object_models import ShareObject
from dataall.base.context import get_context
from dataall.modules.shares_base.services.shares_enums import ShareObjectStatus
from dataall.modules.notifications.db.notification_repositories import NotificationRepository
from dataall.modules.notifications.services.ses_email_notification_service import SESEmailNotificationService
from dataall.modules.datasets_base.db.dataset_models import DatasetBase

log = logging.getLogger(__name__)


class DataSharingNotificationType(enum.Enum):
    SHARE_OBJECT_SUBMITTED = 'SHARE_OBJECT_SUBMITTED'
    SHARE_ITEM_REQUEST = 'SHARE_ITEM_REQUEST'
    SHARE_OBJECT_APPROVED = 'SHARE_OBJECT_APPROVED'
    SHARE_OBJECT_REJECTED = 'SHARE_OBJECT_REJECTED'
    SHARE_OBJECT_PENDING_APPROVAL = 'SHARE_OBJECT_PENDING_APPROVAL'
    DATASET_VERSION = 'DATASET_VERSION'


class ShareNotificationService:
    """
    Notifications sent to:
        - dataset.SamlAdminGroupName
        - dataset.stewards
        - share.groupUri
    Emails sent to:
        - dataset.SamlAdminGroupName
        - dataset.stewards
        - share.owner (person that opened the request) OR share.groupUri (if group_notifications=true)
    """

    def __init__(self, session, dataset: DatasetBase, share: ShareObject):
        self.dataset = dataset
        self.share = share
        self.session = session
        self.notification_target_users = self._get_share_object_targeted_users()

    def notify_share_object_submission(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}/console/shares/{self.share.shareUri}">share link </a> to take action or view more details'
        msg = f'User {email_id} SUBMITTED share request for dataset {self.dataset.label} for principal {self.share.principalId}'
        subject = f'Data.all | Share Request Submitted for {self.dataset.label}'
        email_notification_msg = msg + share_link_text

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_SUBMITTED.value, msg=msg
        )

        self._create_notification_task(subject=subject, msg=email_notification_msg)
        return notifications

    def notify_persistent_email_reminder(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = (
                f'<br><br>Please visit data.all <a href="{os.environ.get("frontend_domain_url")}'
                f'/console/shares/{self.share.shareUri}">share link</a> '
                f'to review and take appropriate action or view more details.'
            )

        msg_intro = f"""Dear User,
        This is a reminder that a share request for the dataset "{self.dataset.label}" submitted by {email_id} 
        on behalf of principal "{self.share.principalId}" is still pending and has not been addressed.
        """

        msg_end = """Your prompt attention to this matter is greatly appreciated.
        Best regards,
        The Data.all Team
        """

        subject = f'URGENT REMINDER: Data.all | Action Required on Pending Share Request for {self.dataset.label}'
        email_notification_msg = msg_intro + share_link_text + msg_end

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_SUBMITTED.value, msg=msg_intro
        )

        self._create_persistent_reminder_notification_task(subject=subject, msg=email_notification_msg)
        return notifications

    def notify_share_object_approval(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = (
                f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}'
                f'/console/shares/{self.share.shareUri}">share link </a> '
                f'to take action or view more details'
            )
        msg = (
            f'User {email_id} APPROVED share request for dataset {self.dataset.label} '
            f'for principal {self.share.principalId}'
        )
        subject = f'Data.all | Share Request Approved for {self.dataset.label}'
        email_notification_msg = msg + share_link_text

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_APPROVED.value, msg=msg
        )

        self._create_notification_task(subject=subject, msg=email_notification_msg)
        return notifications

    def notify_share_object_rejection(self, email_id: str):
        share_link_text = ''
        if os.environ.get('frontend_domain_url'):
            share_link_text = f'<br><br> Please visit data.all <a href="{os.environ.get("frontend_domain_url")}/console/shares/{self.share.shareUri}">share link </a> to take action or view more details'
        if self.share.status == ShareObjectStatus.Rejected.value:
            msg = f'User {email_id} REJECTED share request for dataset {self.dataset.label} for principal {self.share.principalId}'
            subject = f'Data.all | Share Request Rejected for {self.dataset.label}'
        elif self.share.status == ShareObjectStatus.Revoked.value:
            msg = f'User {email_id} REVOKED share request for dataset {self.dataset.label} for principal {self.share.principalId}'
            subject = f'Data.all | Share Request Revoked for {self.dataset.label}'
        else:
            msg = f'User {email_id} REJECTED/REVOKED share request for dataset {self.dataset.label} for principal {self.share.principalId}'
            subject = f'Data.all | Share Request Rejected / Revoked for {self.dataset.label}'
        email_notification_msg = msg + share_link_text

        notifications = self.register_notifications(
            notification_type=DataSharingNotificationType.SHARE_OBJECT_REJECTED.value, msg=msg
        )

        self._create_notification_task(subject=subject, msg=email_notification_msg)
        return notifications

    def _get_share_object_targeted_users(self):
        targeted_users = list()
        targeted_users.append(self.dataset.SamlAdminGroupName)
        if self.dataset.stewards != self.dataset.SamlAdminGroupName:
            targeted_users.append(self.dataset.stewards)
        targeted_users.append(self.share.groupUri)
        return targeted_users

    def register_notifications(self, notification_type, msg):
        """
        Notifications sent to:
            - dataset.SamlAdminGroupName
            - dataset.stewards
            - share.groupUri
        """
        notifications = []
        for recipient in self.notification_target_users:
            log.info(f'Creating notification for {recipient}, msg {msg}')
            notifications.append(
                NotificationRepository.create_notification(
                    session=self.session,
                    recipient=recipient,
                    notification_type=notification_type,
                    target_uri=f'{self.share.shareUri}|{self.dataset.datasetUri}',
                    message=msg,
                )
            )
        self.session.add_all(notifications)
        return notifications

    def _create_notification_task(self, subject, msg):
        """
        At the moment just for notification_config_type = email, but designed for additional notification types
        Emails sent to:
            - dataset.SamlAdminGroupName
            - dataset.stewards
            - share.owner (person that opened the request) OR share.groupUri (if group_notifications=true)
        """
        share_notification_config = config.get_property(
            'modules.datasets_base.features.share_notifications', default=None
        )
        if share_notification_config:
            for share_notification_config_type in share_notification_config.keys():
                n_config = share_notification_config[share_notification_config_type]
                if n_config.get('active', False) == True:
                    params = n_config.get('parameters', {})
                    notification_recipient_groups_list = [self.dataset.SamlAdminGroupName, self.dataset.stewards]
                    notification_recipient_email_ids = []

                    if share_notification_config_type == 'email':
                        if params.get('group_notifications', False) == True:
                            notification_recipient_groups_list.append(self.share.groupUri)
                        else:
                            notification_recipient_email_ids = [self.share.owner]

                        notification_task: Task = Task(
                            action='notification.service',
                            targetUri=self.share.shareUri,
                            payload={
                                'notificationType': share_notification_config_type,
                                'subject': subject,
                                'message': msg,
                                'recipientGroupsList': notification_recipient_groups_list,
                                'recipientEmailList': notification_recipient_email_ids,
                            },
                        )
                        self.session.add(notification_task)
                        self.session.commit()

                        Worker.queue(engine=get_context().db_engine, task_ids=[notification_task.taskUri])
                else:
                    log.info(f'Notification type : {share_notification_config_type} is not active')
        else:
            log.info('Notifications are not active')

    def _create_persistent_reminder_notification_task(self, subject, msg):
        """
        At the moment just for notification_config_type = email, but designed for additional notification types
        Emails sent to:
            - dataset.SamlAdminGroupName
            - dataset.stewards
        """
        share_notification_config = config.get_property(
            'modules.datasets_base.features.share_notifications', default=None
        )
        if share_notification_config:
            for share_notification_config_type in share_notification_config.keys():
                n_config = share_notification_config[share_notification_config_type]
                if n_config.get('active', False) == True:
                    notification_recipient_groups_list = [self.dataset.SamlAdminGroupName, self.dataset.stewards]

                    if share_notification_config_type == 'email':
                        notification_task: Task = Task(
                            action='notification.service',
                            targetUri=self.share.shareUri,
                            payload={
                                'notificationType': share_notification_config_type,
                                'subject': subject,
                                'message': msg,
                                'recipientGroupsList': notification_recipient_groups_list,
                                'recipientEmailList': [],
                            },
                        )
                        self.session.add(notification_task)
                        self.session.commit()

                        SESEmailNotificationService.send_email_task(
                            subject, msg, notification_recipient_groups_list, []
                        )
                else:
                    log.info(f'Notification type : {share_notification_config_type} is not active')
        else:
            log.info('Notifications are not active')
