import pytest
import os
from sqlwhat.grammar.plsql import ast

crnt_dir = os.path.dirname(__file__)
examples = os.path.join(crnt_dir, 'examples')
#examples_sql_script = os.path.join(crnt_dir, 'examples-sql-script')

def load_examples(dir_path):
    return [[fname, open(os.path.join(dir_path, fname)).read()] 
                for fname in os.listdir(dir_path)
                ]


@pytest.mark.parametrize('name, query', load_examples(examples))
def test_examples(name, query):
    ast.parse(query)

#@pytest.mark.parametrize('name, query', load_examples(examples_sql_script))
#def test_examples_sql_script(name, query):
#    ast.parse(query)


