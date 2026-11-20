#! /bin/bash

set -e

if test "$GITHUB_EVENT_NAME" != "workflow_dispatch"; then
    echo "Not a workflow dispatch. Skipping version update."
    exit 0
fi

base_dir=$(dirname $(realpath "$0"))/../..

if test "$#" -ne 1; then
    echo "Usage: $0 version"
    exit 1
fi
version=$1

echo "Setting version to $version"

sed --in-place "s/^\(VERSION = \)['\"].*/\1'$version'/" $base_dir/autograder/settings/base.py

sed --in-place "s/^\(\s*version: \).*/\1$version/" $base_dir/autograder/rest_api/schema/schema.yml
