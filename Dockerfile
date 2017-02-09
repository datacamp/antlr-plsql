FROM python:3.5

RUN apt-get update && apt-get install -y \
    build-essential \
    default-jdk \
    maven

#WORKDIR /usr/local/lib
RUN cd /usr/local/lib && curl -O documents.datacamp.com/antlr4-4.6.1-SNAPSHOT-complete.jar
ENV CLASSPATH=".:/usr/local/lib/antlr-4.6.1-SNAPSHOT-complete.jar:$CLASSPATH"
RUN echo "java -Xmx500M -cp \"/usr/local/lib/antlr4-4.6.1-SNAPSHOT-complete.jar:$CLASSPATH\" org.antlr.v4.Tool \$@" >> /usr/local/bin/antlr4 && chmod u+x /usr/local/bin/antlr4
RUN echo "alias grun='java org.antlr.v4.runtime.misc.TestRig'" >> ~/.bashrc

COPY . /usr/src/app
WORKDIR /usr/src/app
RUN cd sqlwhat/grammar/plsql && antlr4 -Dlanguage=Python3 -visitor plsql.g4
RUN pip install antlr4-python3-runtime
RUN pip install -r requirements.txt
RUN pip install -e .

CMD make clean test
