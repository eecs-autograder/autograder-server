from argparse import RawTextHelpFormatter
import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import get_random_secret_key

import gnupg


class Command(BaseCommand):
    help = f"""Creates the directory {settings.SECRETS_DIR} and
populates it with secrets files. This includes the Django secret key,
a GPG key pair, and a password for the GPG key pair.

    If any of the secrets already exist, the existing value will be KEPT
    and will NOT be replaced. This is most important for the GPG key,
    as changing it will invalidate all existing email receipts.
    """

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def handle(self, *args, **options):
        os.makedirs(settings.SECRETS_DIR, exist_ok=True)

        if not os.path.exists(settings.SECRET_KEY_FILENAME):
            with open(settings.SECRET_KEY_FILENAME, 'w') as f:
                f.write(get_random_secret_key())

        if not os.path.exists(settings.GPG_KEY_PASSWORD_FILENAME):
            gpg_key_password = get_random_secret_key()
            gpg = gnupg.GPG(gnupghome=settings.SECRETS_DIR)
            input_data = gpg.gen_key_input(
                name_email='admin@autograder.io',
                passphrase=gpg_key_password
            )
            gpg.gen_key(input_data)

            with open(settings.GPG_KEY_PASSWORD_FILENAME, 'w') as f:
                f.write(gpg_key_password)
