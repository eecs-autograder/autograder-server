This repository contains the Django database and web API code.

# Server Dev Setup

This tutorial will walk you through setting up your local machine for modifying
and testing the server code.

## System Requirements

**Supported Operating Systems:**
- Ubuntu 16.04

It may be possible to run the server tests on OSX.
If you decide to try this, you're on your own.
Newer versions of Ubuntu are probably ok, but I haven't verified this.

## Clone and Checkout
```
git clone git@github.com:eecs-autograder/autograder-server.git
cd autograder-server
git checkout develop
```

## Install Docker Community Edition
Ubuntu: https://docs.docker.com/install/linux/docker-ce/ubuntu/#install-docker-ce-1

## Install Postgres
```
sudo apt-get install postgresql-9.5 postgresql-client-9.5 postgresql-contrib-9.5 postgresql-server-dev-9.5
```
Set a password for the 'postgres' user.
```
sudo -u postgres psql -c "alter user postgres with password 'postgres'"
```
If you choose a different password, you'll need to set the AG_DB_PASSWORD
environment variable with your chosen password:
```
export AG_DB_PASSWORD=<password>
```

## Install Redis Server
```
sudo apt-get install redis-server
```

## Install Python 3.8
```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.8 python3.8-venv python3.8-dev
curl https://bootstrap.pypa.io/get-pip.py | sudo python3.8

python3.8 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install wheel
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Running the Unit Tests
To run the tests (takes about 22 minutes on my machine):
```
python3.8 manage.py -v 2 test
```

## Updating schema.yml and Rendering the Schema
This project uses DRF's schema generation as a starting point for discovering
API operations and their URL params. We extend this functionality in
autograder/rest_api/schema.py to add Model Schema generation and to fill in
endpoint details.

To update schema.yml, run:
```
./manage.py generateschema --generator_class autograder.rest_api.schema.AGSchemaGenerator > schema/schema.yml
```

If you are running the full development stack, you may skip the next step.

To render and serve the API using Swagger UI, run (requires Docker):
```
# Run from the project root directory, i.e. "autograder-server"
docker run -d --name ag_schema -p 8080:8080 --env-file schema/env -v $(pwd)/schema:/root swaggerapi/swagger-ui
```
Then navigate to localhost:8080 in your browser. To change the port, change `8080:8080` to `<your port>:8080`, e.g. `9001:8080`.

# Coding Standards
To run pycodestyle (settings are in setup.cnf):
```
pycodestyle autograder
```
To run pydocstyle (settings are in setup.cnf):
```
pydocstyle autograder
```
- Unless otherwise stated, code must comply with [PEP 8](https://www.python.org/dev/peps/pep-0008/).
- Limit lines to a maximum of 99 characters.
- Use type annotations for all new code, unless the code is highly dynamic.
- Don't use acronyms other than the ones listed below:
    - 'ag' = 'autograder'
    - 'hg' = 'handgrading'
- Avoid abbreviations. Shortening long, frequently used words can be ok,
especially in more local contexts.
- Use these import aliases:
    - `import autograder.core.models as ag_models`
        - NOTE: Do NOT import `autograder.core.models` from modules inside
        that package.
    - `import autograder.core.fields as ag_fields`
    - `import autograder.rest_api.permissions as ag_permissions`
    - `import autograder.rest_api.serializers as ag_serializers`
    - `import autograder.core.utils as core_ut`
    - `import autograder.handgrading.models as hg_models`
- Don't use \ to wrap lines (except in `with`-statements). Use parentheses.
- Use a single leading underscore for non-public names.
- When a closing brace, bracket, or parenthesis is on its own line, align
it with the first character of the line that starts the multiline construct:
```
my_list = [
    'spam',
    'egg',
    'waluigi,
]
```
- When using a hanging indent for a multiline `if` condition, indent an extra level:
```
if (spam_spam_wonderful_spam
        and egg and waluigi):
    print('waaaaluigi')
```
- Put line breaks before binary operators.
