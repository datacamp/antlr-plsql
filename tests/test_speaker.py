import pytest
import os
from antlr_plsql import ast
from antlr_ast.ast import Speaker
import yaml


@pytest.fixture
def speaker():
    return Speaker(
        nodes={"SelectStmt": "SELECT statement", "Call": "function call `{node.name}`"},
        fields={"target_list": "target list"},
    )


def test_select_statement(speaker):
    select = ast.parse("SELECT x FROM y", start="subquery")
    assert speaker.describe(select, "{node_name}") == "SELECT statement"


def test_select_target_list(speaker):
    select = ast.parse("SELECT x FROM y", start="subquery")
    assert speaker.describe(
        select, field="target_list", fmt="The {field_name} of {node_name}"
    )


def test_call_name(speaker):
    call = ast.parse("COUNT(*)", start="standard_function")
    assert speaker.describe(call, fmt="{node_name}") == "function call `COUNT`"


@pytest.mark.parametrize(
    "start, code",
    [
        ("selected_element", "id as id2"),
        ("binary_expression", "1 + 2"),
        ("standard_function", "COUNT(*)"),
        ("selected_element", "id"),
        # TODO: from_clause terminal used to be dropped, but after rewrite that keeps the data type, which is a list
        #  remove visit_From_clause?
        # ('from_clause', 'FROM a JOIN b'),
        ("order_by_clause", "ORDER BY id"),
        ("subquery", "SELECT x FROM y"),
        ("order_by_elements", "id ASC"),
        ("selected_element", "*"),
        ("unary_expression", "-1"),
        ("subquery", "SELECT x FROM y UNION SELECT m FROM n"),
    ],
)
def test_print_speaker(code, start):
    speaker = Speaker(**yaml.safe_load(open("antlr_plsql/speaker.yml")))

    tree = ast.parse(code, start=start)

    print("\n\n{} -----------------------\n\n".format(tree.__class__.__name__))
    # node printout
    print(speaker.describe(tree))
    # fields
    for field_name in tree._fields:
        print(
            speaker.describe(
                tree, field=field_name, fmt="The {field_name} of the {node_name}"
            )
        )
