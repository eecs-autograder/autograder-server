This repository contains the Django database and web API code.
For information about contributing to Autograder.io, see our
[contributing guide](https://github.com/eecs-autograder/autograder.io/blob/master/CONTRIBUTING.md).

# Server Dev Setup

This tutorial will walk you through setting up your local machine for modifying
and testing the server code.

## System Requirements

**Supported Operating Systems:**
- Ubuntu 20.04 or later

It may be possible to run the server tests on OSX.
If you decide to try this, you're on your own.
Newer versions of Ubuntu are probably ok, but may require extra effort to
install Postgres 9.5 or change the configuration to use a newer version
(the latter applies to full stack development and deployment).

## Clone and Checkout
```
git clone git@github.com:eecs-autograder/autograder-server.git
cd autograder-server
git checkout develop
```

## Install Docker Community Edition
Ubuntu: https://docs.docker.com/install/linux/docker-ce/ubuntu/#install-docker-ce-1

## Install Postgres
Postgres is required to run the test suite. The simplest way to set this up is to run an official Postgres docker container. Replace <version> with your desired version of postgres:
```
docker run -itd postgres:<version>
```
# FIXME: get the correct command from other machine^^^

## Install Redis Server
```
sudo apt-get install redis-server
```

## Install Python 3.10
```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.10 python3.10-distutils python3.10-venv
curl https://bootstrap.pypa.io/get-pip.py | sudo python3.10

python3.10 -m venv venv
source venv/bin/activate

pip install pip-tools wheel
pip-sync requirements.txt requirements-dev.txt
```

You can then run `pipenv shell` to start a shell in the virtual environment,
or if you prefer you can prefix the python commands below with `pipenv run`.

If you run into errors installing psycopg2, please refer to https://www.psycopg.org/docs/install.html#build-prerequisites for troubleshooting tips.

### Updating Packages
This section contains some useful reference commands for pip-tools.
```
# Note: After running any of these variants of `pip-compile`, you should
# run `pip-sync requirements.txt requirements-dev.txt`
# (or `./install_pip_packages.sh`, which is an alias script for this command).

# Update one non-dev (listed in requirements.in) package
pip-compile -P <package name>

# Update one dev (listed in requirements-dev.in) package
pip-compile requirements-dev.in -P <package name>

# Update all non-dev packages
pip-compile --upgrade

# Update all dev packages
pip-compile requirements-dev.in --upgrade
```

To install a new non-dev package, add it to requirements.in and then run
`pip-compile` and `./install_pip_packages.sh`.

To install a new dev package, add it to requirements-dev.in and then run
`pip-compile requirements-dev.in` and `./install_pip_packages.sh`.

## Generate Secrets
Run the following command to generate Django and GPG secrets.
```
python3.10 generate_secrets.py
```

## Running the Unit Tests
To run the tests (takes about 15 minutes on my machine):
```
./manage.py -v 2 test
```

## Updating schema.yml and Rendering the Schema
This project uses DRF's schema generation as a starting point for discovering
API operations and their URL params. We extend this functionality in
autograder/rest_api/schema.py to add Model Schema generation and to fill in
endpoint details.

To update schema.yml, run:
```
./manage.py generateschema --generator_class autograder.rest_api.schema.AGSchemaGenerator > autograder/rest_api/schema/schema.yml
```

If you are running the full development stack, you may skip the next step.

To render and serve the API using Swagger UI, run (requires Docker):
```
# Run from the project root directory, i.e. "autograder-server"
docker run -d --name ag_schema -p 8080:8080 --env-file schema/env -v $(pwd)/schema:/root swaggerapi/swagger-ui
```
Then navigate to localhost:8080 in your browser. To change the port, change `8080:8080` to `<your port>:8080`, e.g. `9001:8080`.

# Coding Standards
In addition to the items listed here, all source code must follow our
[Python coding standards](https://github.com/eecs-autograder/autograder.io/blob/master/coding_standards_python.md).

This project uses `pycodestyle`, `pydocstyle`, and `mypy` as linters. They can
be run using the following commands:
```
pycodestyle autograder
pydocstyle autograder
sh run_mypy.sh
```

Use these import aliases for commonly-used modules:
    - `import autograder.core.models as ag_models`
        - NOTE: Do NOT import `autograder.core.models` from modules inside
        that package.
    - `import autograder.core.fields as ag_fields`
    - `import autograder.rest_api.permissions as ag_permissions`
    - `import autograder.rest_api.serializers as ag_serializers`
    - `import autograder.core.utils as core_ut`
    - `import autograder.handgrading.models as hg_models`
