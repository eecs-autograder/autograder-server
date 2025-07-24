#! /bin/bash

base_dir=$(dirname $(realpath "$0"))/..

if test "$#" -ne 1; then
    echo "Usage: $0 version"
    exit 1
fi
version=$1

sed --in-place "s/^\(VERSION = \)['\"].*/\1'$version'/" $base_dir/autograder/settings/base.py

sed --in-place "s/^\(\s*version: \).*/\1$version/" $base_dir/autograder/rest_api/schema/schema.yml
#   version: 0.0.0.dev0
