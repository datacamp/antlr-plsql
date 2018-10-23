import pytest
import os
from antlr_ast import AntlrException
from antlr_plsql import ast


def test_ast_parse_strict():
    with pytest.raises(AntlrException):
        ast.parse("SELECT x FROM ____", strict=True)  # ____ is ungrammatical


def test_unparsed_to_text():
    sql_txt = "SELECT CURSOR (SELECT a FROM b) FROM c"
    tree = ast.parse(sql_txt)
    cursor = tree.body[0].target_list[0]

    assert isinstance(cursor, ast.UnaryExpr)
    assert isinstance(cursor.expr, ast.Unshaped)
    assert cursor._get_text(sql_txt) == "CURSOR (SELECT a FROM b)"
    assert cursor.expr._get_text(sql_txt) == "(SELECT a FROM b)"


def test_ast_dump():
    sql_txt = "SELECT a, b FROM x WHERE a < 10"
    tree = ast.parse(sql_txt)
    tree._dump()


@pytest.mark.parametrize(
    "sql_text, start",
    [
        ("SELECT a, b FROM x WHERE a < 10;", "sql_script"),
        ("SELECT * FROM x", "sql_script"),
        ("SELECT CURSOR (SELECT a FROM b) FROM c", "sql_script"),
        ("SELECT a FROM x", "subquery"),
        ("WHERE x < 10", "where_clause"),
    ],
)
def test_ast_dumps_noerr(sql_text, start):
    tree = ast.parse(sql_text, start)
    d = tree._dumps()


def test_ast_dumps_unary():
    tree = ast.parse("-1", "unary_expression")
    assert tree._dump() == {"type": "UnaryExpr", "data": {"expr": "1", "op": "-"}}


def test_select_fields_shaped():
    select = ast.parse(
        """
    SELECT a,b 
    FROM x,y 
    GROUP BY a, b
    ORDER BY a, b
    
    """,
        "subquery",
    )
    for field in select._get_field_names():
        assert not isinstance(getattr(select, field), ast.Unshaped)


@pytest.mark.parametrize(
    "sql_text",
    [
        "SELECT a FROM co AS c INNER JOIN ec AS e ON c.code = e.code",
        "SELECT a FROM co AS c INNER JOIN ec ON c.code = ec.code",
        "SELECT a FROM co INNER JOIN ec AS e ON co.code = e.code",
        "SELECT a FROM co INNER JOIN ec ON co.code = ec.code",
    ],
)
def test_inner_join(sql_text):
    tree = ast.parse(sql_text)
    assert tree.body[0].from_clause.join_type == "INNER"


@pytest.mark.parametrize(
    "sql_text",
    [
        "SELECT a AS c FROM d RIGHT JOIN e ON f.g = h.j RIGHT JOIN i ON j.k = l.m",
        "SELECT a AS c FROM d RIGHT JOIN e ON f.g = h.j RIGHT JOIN i ON j.k = l.m ORDER BY n",
        "SELECT a.b AS c FROM d RIGHT JOIN e ON f.g = h.j RIGHT JOIN i ON j.k = l.m",
        "SELECT a.b AS c FROM d RIGHT JOIN e ON f.g = h.j RIGHT JOIN i ON j.k = l.m ORDER BY n",
    ],
)
def test_double_inner_join(sql_text):
    tree = ast.parse(sql_text)
    frm = tree.body[0].from_clause
    assert frm.join_type == "RIGHT"
    assert frm.right.fields == ["i"]
    assert frm.left.join_type == "RIGHT"
    assert frm.left.left.fields == ["d"]
    assert frm.left.right.fields == ["e"]


@pytest.mark.parametrize(
    "sql_text",
    [
        "SELECT a AS c FROM d as ad RIGHT JOIN e as ae ON f.g = h.j RIGHT JOIN i as ai ON j.k = l.m",
        "SELECT a AS c FROM d as ad RIGHT JOIN e as ae ON f.g = h.j RIGHT JOIN i as ai ON j.k = l.m ORDER BY n",
        "SELECT a.b AS c FROM d as ad RIGHT JOIN e as ae ON f.g = h.j RIGHT JOIN i as ai ON j.k = l.m",
        "SELECT a.b AS c FROM d as ad RIGHT JOIN e as ae ON f.g = h.j RIGHT JOIN i as ai ON j.k = l.m ORDER BY n",
    ],
)
def test_double_inner_join_with_aliases(sql_text):
    tree = ast.parse(sql_text)
    frm = tree.body[0].from_clause
    assert frm.join_type == "RIGHT"
    assert frm.right.arr[0].fields == ["i"]  # not good
    assert frm.left.join_type == "RIGHT"
    assert frm.left.left.arr[0].fields == ["d"]  # not good
    assert frm.left.right.arr[0].fields == ["e"]  # not good


def test_ast_select_paren():
    node = ast.parse("(SELECT a FROM b)", "subquery")
    assert isinstance(node, ast.SelectStmt)


def ast_examples_parse(fname):
    import yaml

    dirname = os.path.dirname(__file__)
    data = yaml.load(open(dirname + "/" + fname))
    res = {}
    for start, cmds in data["code"].items():
        res[start] = []
        for cmd in cmds:
            res[start].append([cmd, repr(ast.parse(cmd, start, strict=True))])
    print(res)
    filename = "dump_" + fname
    with open(dirname + "/" + filename, "w") as out_f:
        yaml.dump(res, out_f)
    return filename


@pytest.mark.parametrize("fname", ["v0.2.yml", "v0.3.yml", "v0.5.yml"])
def test_ast_examples_parse(fname):
    return ast_examples_parse(fname)
