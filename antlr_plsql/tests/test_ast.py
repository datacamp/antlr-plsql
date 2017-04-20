import pytest
import os
from antlr_plsql import ast

def test_ast_parse_strict():
    with pytest.raises(ast.AntlrException):
        ast.parse("SELECT x FROM ____", strict = True)   # ____ is ungrammatical

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

@pytest.mark.parametrize('sql_text, start', [
    ("SELECT a, b FROM x WHERE a < 10;", "sql_script"),
    ("SELECT * FROM x", "sql_script"),
    ("SELECT CURSOR (SELECT a FROM b) FROM c", "sql_script"),
    ("SELECT a FROM x", "subquery"),
    ("WHERE x < 10", "where_clause"),
    ])
def test_ast_dumps_noerr(sql_text, start):
    tree = ast.parse(sql_text, start)
    d = tree._dumps()

def test_ast_dumps_unary():
    tree = ast.parse("-1", "unary_expression")
    assert tree._dump() == {'type': 'UnaryExpr',
                            'data': {'expr': '1', 'op': '-'}
                            }

def test_select_fields_shaped():
    select = ast.parse("""
    SELECT a,b 
    FROM x,y 
    GROUP BY a, b
    ORDER BY a, b
    
    """, "subquery")
    for field in select._get_field_names():
        assert not isinstance(getattr(select, field), ast.Unshaped)

def test_ast_select_paren():
    node = ast.parse("(SELECT a FROM b)", 'subquery')
    assert isinstance(node, ast.SelectStmt)

@pytest.mark.parametrize('fname', [
        'v0.2.yml',
        'v0.3.yml'
        ])
def test_ast_examples_parse(fname):
    import yaml
    dirname = os.path.dirname(__file__)
    data = yaml.load(open(dirname + '/' + fname))
    res = {}
    for start, cmds in data['code'].items():
        res[start] = []
        for cmd in cmds: res[start].append([cmd, repr(ast.parse(cmd, start, strict=True))])
    print(res)
    with open(dirname + '/dump_' + fname, 'w') as out_f:
        yaml.dump(res, out_f)
