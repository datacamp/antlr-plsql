Setup ANTLR grammar
-------------------

```
docker run -it -v ${PWD}:/output $CONTAINER\_ID /bin/bash
# inside container
cd /output
antlr4 -Dlanguage=Python3 $GRAMMAR_FILE.g4
```
