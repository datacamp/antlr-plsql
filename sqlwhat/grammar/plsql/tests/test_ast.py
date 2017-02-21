import pytest
from sqlwhat.grammar.plsql import ast

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

def test_ast_select_union():
    node = ast.parse("SELECT a FROM b UNION SELECT x FROM y", 'subquery')
    assert isinstance(node, ast.BinaryExpr)
    assert node.op == "UNION"
