#! /usr/bin/env python3

"""
Inspect a docker image without pulling it.
Ported from https://ops.tips/blog/inspecting-docker-image-without-pull/
"""

import argparse
import json

import requests


def main():
    args = parse_args()
    result = inspect_remote_image(args.full_image_name)
    print(json.dumps(result, indent=4))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'full_image_name', help='The full image name, including tag or digest.')

    return parser.parse_args()


def inspect_remote_image(full_image_name: str):
    image, tag = parse_repository_tag(full_image_name)
    token = get_auth_token(image)
    digest = get_image_digest(image, tag, token)

    response = requests.get(
        f'https://registry-1.docker.io/v2/{image}/blobs/{digest}',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
    )
    response.raise_for_status()
    return response.json()


def get_auth_token(image: str):
    response = requests.get(
        f'https://auth.docker.io/token?scope=repository:{image}:pull&service=registry.docker.io',
        headers={
            'Content-Type': 'application/json',
        }
    )
    response.raise_for_status()
    return response.json()['token']


def get_image_digest(image: str, tag: str, token: str):
    response = requests.get(
        f'https://registry-1.docker.io/v2/{image}/manifests/{tag}',
        headers={
            'Accept': 'application/vnd.docker.distribution.manifest.v2+json',
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
    )
    if response.status_code == 401:
        raise ImageDigestRequestUnauthorizedError(response)
    response.raise_for_status()
    return response.json()['config']['digest']


# From https://github.com/docker/docker-py/blob
#              /c6a33f25dc7fc172c69b8935e8c1e6b7aa44be8f/docker/utils/utils.py#L200
def parse_repository_tag(repo_name: str):
    image_name, tag = _split_repo_tag(repo_name)
    if '/' not in image_name:
        image_name = 'library/' + image_name
    return image_name, tag


def _split_repo_tag(repo_name: str):
    parts = repo_name.rsplit('@', 1)
    if len(parts) == 2:
        return tuple(parts)

    parts = repo_name.rsplit(':', 1)
    if len(parts) == 2 and '/' not in parts[1]:
        return tuple(parts)

    return repo_name, None


class ImageDigestRequestUnauthorizedError(requests.RequestException):
    pass


if __name__ == '__main__':
    main()
