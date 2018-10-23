import pytest
import os
from antlr_plsql import ast
from tests.test_ast import ast_examples_parse

crnt_dir = os.path.dirname(__file__)
examples = os.path.join(crnt_dir, "examples")
# examples_sql_script = os.path.join(crnt_dir, "examples-sql-script")


def load_examples(dir_path):
    return [
        [fname, open(os.path.join(dir_path, fname)).read()]
        for fname in os.listdir(dir_path)
    ]


# @pytest.mark.examples
@pytest.mark.parametrize("name, query", load_examples(examples))
def test_examples(name, query):
    ast.parse(query)


# @pytest.mark.parametrize("name, query", load_examples(examples_sql_script))
# def test_examples_sql_script(name, query):
#     ast.parse(query)


def load_dump(fname):
    import yaml

    dirname = os.path.dirname(__file__)
    dump_data = yaml.load(open(dirname + "/" + fname))

    all_cmds = []
    for start, cmds in dump_data.items():
        for cmd, res in cmds:
            all_cmds.append((start, cmd, res))
    return all_cmds


@pytest.mark.parametrize(
    "start,cmd,res",
    [
        *load_dump(ast_examples_parse("v0.2.yml")),
        *load_dump(ast_examples_parse("v0.3.yml")),
        *load_dump(ast_examples_parse("v0.5.yml")),
    ],
)
def test_dump(start, cmd, res):
    assert repr(ast.parse(cmd, start, strict=True)) == res
