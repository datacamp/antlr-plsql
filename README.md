# antlr-plsql

[![Build Status](https://travis-ci.org/datacamp/antlr-plsql.svg?branch=master)](https://travis-ci.org/datacamp/antlr-plsql)
[![PyPI version](https://badge.fury.io/py/antlr-plsql.svg)](https://badge.fury.io/py/antlr-plsql)

## Development

ANTLR requires Java, so we suggest you use Docker when building grammars. The `Makefile` contains directives to clean, build, test and deploy the ANTLR grammar. It does not run Docker itself, so run `make` inside Docker.

### Build the grammar

```bash
docker build -t antlr_plsql .
docker run -it -v ${PWD}:/usr/src/app antlr_plsql make build
```

### Develop

ANTLR requires Java, so we suggest you use Docker when building grammars. The `Makefile` contains directives to clean, build, test and deploy the ANTLR grammar. It does not run Docker itself, so run `make` inside Docker.

```bash
# Build the docker container
docker build -t antlr_plsql .

# Run the container to build the python and js grammars
# Write parser files to local file system through volume mounting
docker run -it -v ${PWD}:/usr/src/app antlr_plsql make build
```

Now that the Python parsing files are available, you can install them with `pip`:

```bash
pip install -r requirements.txt
pip install -e .
```

And parse SQL code in Python:

```python
from antlr_plsql import ast
ast.parse("SELECT a from b")
```

If you're actively developing on the ANLTR grammar or the tree shaping, it's a good idea to set up the [AST viewer](https://github.com/datacamp/ast-viewer) locally so you can immediately see the impact of your changes in a visual way.

- Clone the ast-viewer repo and build the Docker image according to the instructions.
- Spin up a docker container that volume mounts the Python package, symlink-installs the package and runs the server on port 3000:

```bash
docker run -it \
  -u root \
  -v ~/workspace/antlr-plsql:/app/app/antlr-plsql \
  -p 3000:3000 \
  ast-viewer \
  /bin/bash -c "echo 'Install development requirements in development:' \
    && pip install --no-deps -e app/antlr-plsql \
    && python3 run.py"
```

When simultaneously developing other packages, volume mount and install those too:

```bash
docker run -it \
  -u root \
  -v ~/workspace/antlr-ast:/app/app/antlr-ast \
  -v ~/workspace/antlr-plsql:/app/app/antlr-plsql \
  -v ~/workspace/antlr-tsql:/app/app/antlr-tsql \
  -p 3000:3000 \
  ast-viewer \
  /bin/bash -c "echo 'Install development requirements in development:' \
    && pip install --no-deps -e app/antlr-ast \
    && pip install --no-deps -e app/antlr-plsql \
    && pip install --no-deps -e app/antlr-tsql \
    && python3 run.py"
```

- If you update the tree shaping logic in this repo, the app will auto-update.
- If you change the grammar, you will have to first rebuild the grammar (with the `antlr_plsql` docker image) and restart the `ast-viewer` container.

## Travis deployment

- Builds the Docker image
- Runs the Docker image to build the grammar, run the unit tests
- Commits the generated grammar files to the `builds` (for `master`) and `builds-dev` (for `dev`) branches.
- Builds the grammar and deploys the resulting python and js files to PyPi when a new release is made.
