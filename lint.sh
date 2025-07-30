#! /bin/bash

set -ex

pycodestyle autograder
pydocstyle autograder
./lint/run_mypy.sh
python3 manage.py makemigrations --check
python3 manage.py generateschema --generator_class autograder.rest_api.schema.AGSchemaGenerator > /tmp/schema-check.yml
diff -q autograder/rest_api/schema/schema.yml /tmp/schema-check.yml

test -d lint/validate_schema/node_modules || (cd lint/validate_schema && npm install @apidevtools/swagger-parser@10.1.0)
node lint/validate_schema/validate_schema.js
