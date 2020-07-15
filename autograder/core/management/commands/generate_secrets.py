from argparse import RawTextHelpFormatter
import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import get_random_secret_key

from cryptography.fernet import Fernet


class Command(BaseCommand):
    help = """Creates the file autograder/settings/secrets.json and
populates it with secrets under the following keys:
- secret_key: A random string of characters used to set the
    SECRET_KEY Django setting.
- submission_email_verification_key: A hex-encoded Fernet key
    used to verify submission receipt emails. Used to set the
    SUBMISSION_EMAIL_VERIFICATION_KEY custom setting.

    If either of these secrets are already present in secrets.json,
    the existing value will be KEPT and will NOT be replaced. This is
    most important for submission_email_verification_key, as changing
    this value will invalidate all existing email receipts.
    """

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def handle(self, *args, **options):
        secrets = {}
        if os.path.exists(settings.SECRETS_FILENAME):
            with open(settings.SECRETS_FILENAME) as f:
                secrets = json.load(f)

        new_secrets = False
        if 'secret_key' not in secrets:
            secrets['secret_key'] = get_random_secret_key()
            new_secrets = True
        if 'submission_email_verification_key' not in secrets:
            secrets['submission_email_verification_key'] = Fernet.generate_key().hex()
            new_secrets = True

        if new_secrets:
            with open(settings.SECRETS_FILENAME, 'w') as f:
                json.dump(secrets, f)
