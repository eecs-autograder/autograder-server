import argparse
from argparse import RawTextHelpFormatter
import json
import os

import autograder.settings.base as settings
from django.core.management.utils import get_random_secret_key

import gnupg


def main():
    parse_args()

    os.makedirs(settings.SECRETS_DIR, exist_ok=True)

    if not os.path.exists(settings.SECRET_KEY_FILENAME):
        with open(settings.SECRET_KEY_FILENAME, 'w') as f:
            f.write(get_random_secret_key())

    # We create the file settings.GPG_KEY_PASSWORD_FILENAME last.
    # If it doesn't exist, then we need to generate gpg secrets.
    if not os.path.exists(settings.GPG_KEY_PASSWORD_FILENAME):
        gpg_key_password = get_random_secret_key()
        gpg = gnupg.GPG(gnupghome=settings.SECRETS_DIR)
        input_data = gpg.gen_key_input(
            name_email=settings.EMAIL_FROM_ADDR,
            passphrase=gpg_key_password
        )
        gpg_key_id = gpg.gen_key(input_data)

        with open(settings.GPG_KEY_ID_FILENAME, 'w') as f:
            f.write(str(gpg_key_id.fingerprint))

        with open(settings.GPG_KEY_PASSWORD_FILENAME, 'w') as f:
            f.write(gpg_key_password)


def parse_args():
    parser = argparse.ArgumentParser(description=f"""Creates the directory {settings.SECRETS_DIR} and
populates it with secrets files. This includes the Django secret key,
a GPG key pair, and a password for the GPG key pair.

If any of the secrets already exist, the existing value will be KEPT
and will NOT be replaced. This is most important for the GPG key,
as changing it will invalidate all existing email receipts.
""")
    parser.formatter_class = RawTextHelpFormatter

    return parser.parse_args()


if __name__ == '__main__':
    main()
