# sqlwhat

[![Build Status](https://travis-ci.org/datacamp/sqlwhat.svg?branch=master)](https://travis-ci.org/datacamp/sqlwhat)

First steps in sqlwhat

## Notes michael

Setup ANTLR grammar
-------------------

```
docker run -it -v ${PWD}:/output $CONTAINER\_ID /bin/bash
# inside container
cd /output
antlr4 -Dlanguage=Python3 $GRAMMAR_FILE.g4
```

Running unit tests
------------------

In order to install psycopg2 in a virtualenv, I [needed to run](http://stackoverflow.com/a/39244687/1144523)..

```
env LDFLAGS="-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib" pip install --no-cache psycopg2
```
