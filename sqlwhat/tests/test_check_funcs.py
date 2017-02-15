from sqlwhat.check_funcs import check_statement, check_clause, has_equal_ast
from sqlwhat.selectors import ast
from sqlwhat.State import State
from pythonwhat.Reporter import Reporter
from pythonwhat.Test import TestFail as TF
import pytest

def prepare_state(solution_code, student_code):
    return State(
        student_code = student_code,
        solution_code = solution_code,
        reporter = Reporter(),
        # args below should be ignored
        pre_exercise_code = "NA", 
        student_result = [], solution_result = [],
        student_conn = None, solution_conn = None)

def test_has_equal_ast_pass_identical():
    state = prepare_state("SELECT id, name FROM Trips", "SELECT id, name FROM Trips")
    has_equal_ast(state=state)

def test_has_equal_ast_pass_clause_caps():
    state = prepare_state("select id, name from Trips", "SELECT id, name FROM Trips")
    has_equal_ast(state=state)

def test_has_equal_ast_pass_spacing():
    state = prepare_state("SELECT id,name from Trips", "SELECT id, name FROM Trips")
    has_equal_ast(state=state)

def test_has_equal_ast_pass_unparsed():
    query = "SELECT CURSOR (SELECT * FROM TRIPS) FROM Trips"
    state = prepare_state(query, query)
    has_equal_ast(state=state)

def test_has_equal_ast_fail_quoted_column():
    state = prepare_state('SELECT "id", "name" FROM "Trips"', "SELECT id, name FROM Trips")
    with pytest.raises(TF): has_equal_ast(state=state)

def test_check_statement_pass():
    state = prepare_state("SELECT id, name FROM Trips", "SELECT id FROM Trips")
    child = check_statement("select", 0, state=state)
    assert isinstance(child.student_ast, ast.SelectStmt)
    assert isinstance(child.solution_ast, ast.SelectStmt)

def test_check_statement_fail():
    state = prepare_state("SELECT id, name FROM Trips", "INSERT INTO Trips VALUES (1)")
    with pytest.raises(TF): check_statement("select", 0, state=state)

def test_check_clause_pass():
    state = prepare_state("SELECT id FROM Trips WHERE id > 3", "SELECT id FROM Trips WHERE id>3")
    select = check_statement("select", 0, state=state)
    check_clause("where_clause", state=select)

def test_check_clause_fail():
    state = prepare_state("SELECT id FROM Trips WHERE id > 3", "SELECT id FROM Trips WHERE id>4")
    select = check_statement("select", 0, state=state)
    check_clause("where_clause", state=select)

