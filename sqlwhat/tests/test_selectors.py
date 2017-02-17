from sqlwhat.selectors import Selector, dispatch, ast
from sqlwhat.State import State
from pythonwhat.Reporter import Reporter
from pythonwhat.Test import TestFail as TF
import pytest

def test_selector_standalone():
    from ast import Expr, Num        # use python's builtin ast library
    Expr._priority = 0; Num._priority = 1
    node = Expr(value = Num(n = 1))
    sel = Selector(Num)
    sel.visit(node)
    assert isinstance(sel.out[0], Num)

def test_selector_on_self():
    star = ast.Star(None)
    sel = Selector(ast.Star)
    sel.visit(star)
    assert sel.out[0] == star

# tests using actual parsed ASTs ----------------------------------------------

def build_and_run(sql_expr, ast_class, priority=None):
    tree = ast.parse(sql_expr)
    sel = Selector(ast_class, priority=priority)
    sel.visit(tree)
    return sel.out

def test_selector_on_script():
    out = build_and_run("SELECT id FROM artists", ast.SelectStmt)
    assert len(out) == 1
    assert type(out[0]) == ast.SelectStmt

def test_selector_set_high_priority():
    out = build_and_run("SELECT id FROM artists", ast.Identifier, priority=999)
    assert len(out) == 2
    assert all(type(v) == ast.Identifier for v in out)

def test_selector_set_low_priority():
    out = build_and_run("SELECT id FROM artists", ast.Identifier, priority=0)
    assert len(out) == 0

def test_selector_omits_subquery():
    out = build_and_run("SELECT a FROM x WHERE a = (SELECT b FROM y)", ast.SelectStmt)
    assert len(out) == 1
    assert all(type(v) == ast.SelectStmt for v in out)
    assert out[0].target_list[0].fields == ['a']

def test_selector_includes_subquery():
    out = build_and_run("SELECT a FROM x WHERE a = (SELECT b FROM y)", ast.SelectStmt, priority=999)
    select1 = out[1]
    select2 = ast.parse("SELECT b FROM y", start='subquery')    # subquery is the parser rule for select statements
    assert repr(select1) == repr(select2)

def test_dispatch_select():
    tree = ast.parse("SELECT id FROM artists")
    selected = dispatch("statement", "select", 0, tree)
    assert type(selected) == ast.SelectStmt


