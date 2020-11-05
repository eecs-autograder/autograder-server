from __future__ import annotations

import itertools
from typing import Any, Collection, Dict, List, cast

from django.contrib.auth.models import User
from django.contrib.postgres import fields as pg_fields
from django.core import exceptions
from django.db import models, transaction

from autograder.core.constants import MAX_CHAR_FIELD_LEN

from .. import ag_model_base
from ..project import Project
from . import verification


class GroupInvitationManager(ag_model_base.AutograderModelManager['GroupInvitation']):
    # Technically this violates the Liskov Substitution Principal.
    # However, GroupInvitation.objects will always be an instance of
    # GroupInvitationManager typed as such, so we know this to be safe.
    def validate_and_create(  # type: ignore
        self,
        sender: User,
        recipients: Collection[User],
        **kwargs: Any
    ) -> GroupInvitation:
        with transaction.atomic():
            if sender in recipients:
                raise exceptions.ValidationError(
                    {'recipients': 'You cannot send an invitation to yourself'})
            verification.verify_users_can_be_in_group(
                tuple(itertools.chain(recipients, (sender,))),
                kwargs['project'], 'recipients')

            project = kwargs['project']
            has_pending_sent = sender.group_invitations_sent.filter(
                project=project).count()
            has_pending_received = sender.group_invitations_received.filter(
                project=project).count()
            if has_pending_sent or has_pending_received:
                raise exceptions.ValidationError(
                    {'pending_invitation':
                        'You may not send any additional group invitations until '
                        'your pending invitations are resolved.'})

            invitation = self.model(sender=sender, **kwargs)
            invitation.save()
            invitation.recipients.add(*recipients)
            invitation.full_clean()
            return invitation


class GroupInvitation(ag_model_base.AutograderModel):
    """
    This class stores an invitation for a set of users to create a
    Group together.
    """
    recipients = models.ManyToManyField(
        User, related_name='group_invitations_received',
        help_text="""The Users that the sender has invited
            to form a submission group together.
            This field is REQUIRED.
            This field may not be empty.""")

    sender = models.ForeignKey(
        User, related_name='group_invitations_sent',
        on_delete=models.CASCADE,
        help_text="""The User who created this invitation.
            This field is REQUIRED.""")

    _recipients_who_accepted = pg_fields.ArrayField(
        models.CharField(max_length=MAX_CHAR_FIELD_LEN, blank=False),
        default=list, blank=True
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                related_name='group_invitations')

    objects = GroupInvitationManager()

    def clean(self) -> None:
        super().clean()
        if not self.recipients.count():
            raise exceptions.ValidationError(
                {'recipients': 'This field may not be empty'})

    @property
    def sender_username(self) -> str:
        """
        The username of the User that sent this invitation.
        """
        return self.sender.username

    @property
    def recipient_usernames(self) -> List[str]:
        """
        The usernames of the Users that will receive this invitation.
        """
        # Use python sorting instead of DB order by to take advantage
        # of prefetching.
        return [user.username for user in
                sorted(self.recipients.all(), key=lambda user: user.username)]

    @property
    def recipients_who_accepted(self) -> List[str]:
        """
        A list of usernames indicating which invitees have accepted
        this invitation.
        This field is READ ONLY.
        """
        return list(self._recipients_who_accepted)

    @property
    def all_recipients_accepted(self) -> bool:
        """
        Returns True if all invited users have accepted the invitation.
        """
        return set(self.recipient_usernames) == set(self._recipients_who_accepted)

    def recipient_accept(self, user: User) -> None:
        """
        Marks the given user as having accepted the group invitation.
        """
        if user == self.sender:
            return

        if user.username in self.recipients_who_accepted:
            return

        self._recipients_who_accepted.append(user.username)
        self.save()

    SERIALIZABLE_FIELDS = (
        'pk',
        'project',
        'sender',
        'recipients',
        'sender_username',
        'recipient_usernames',
        'recipients_who_accepted',
    )

    SERIALIZE_RELATED = ('sender', 'recipients')

    def to_dict(self) -> Dict[str, object]:
        result = super().to_dict()
        cast(
            List[Dict[str, object]], result['recipients']
        ).sort(key=lambda user: cast(str, user['username']))
        return result
