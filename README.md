antlr-plsql
===========

Setup ANTLR grammar
-------------------

### Docker

```
docker run -it -v ${PWD}:/output $CONTAINER\_ID /bin/bash
# inside container
cd /output
antlr4 -Dlanguage=Python3 $GRAMMAR_FILE.g4
```

### Vagrant

```
vagrant up
vagrant ssh
# inside vagrant box
cd /vagrant
make build
```

Running unit tests
------------------

`make test`
