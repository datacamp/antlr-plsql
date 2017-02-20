from sqlwhat.check_funcs import check_statement, check_clause, has_equal_ast
from sqlwhat import check_funcs as cf
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

def test_has_equal_ast_manual_fail():
    query = "SELECT id, name FROM Trips"
    state = prepare_state(query, query)
    with pytest.raises(TF): 
        child = check_statement(state, "select")
        has_equal_ast(child, sql="SELECT * FROM Trips", start="subquery")

def test_has_equal_ast_manual_pass():
    query = "SELECT id, name FROM Trips"
    state = prepare_state(query, query)
    child = check_statement(state, "select")
    has_equal_ast(child, sql=query, start="subquery")

def test_check_statement_pass():
    state = prepare_state("SELECT id, name FROM Trips", "SELECT id FROM Trips")
    child = check_statement(state, "select", 0)
    assert isinstance(child.student_ast, ast.SelectStmt)
    assert isinstance(child.solution_ast, ast.SelectStmt)

def test_check_statement_fail():
    state = prepare_state("SELECT id, name FROM Trips", "INSERT INTO Trips VALUES (1)")
    with pytest.raises(TF): check_statement(state, "select", 0)

def test_check_clause_pass():
    state = prepare_state("SELECT id FROM Trips WHERE id > 3", "SELECT id FROM Trips WHERE id>3")
    select = check_statement(state, "select", 0)
    check_clause(select, "where_clause")

def test_check_clause_fail():
    state = prepare_state("SELECT id FROM Trips WHERE id > 3", "SELECT id FROM Trips WHERE id>4")
    select = check_statement(state, "select", 0)
    check_clause(select, "where_clause")

@pytest.fixture
def state_tst():
    return prepare_state("SELECT id FROM Trips", "SELECT id FROM Trips WHERE id > 4   ;")

def test_student_typed_itself_pass(state_tst):
    cf.test_student_typed(state_tst, text=state_tst.student_code, fixed=True)

def test_student_typed_fixed_subset_fail(state_tst):
    select = check_statement(state_tst, "select", 0)
    # should fail because the select statement does not include ';'
    with pytest.raises(TF):
        cf.test_student_typed(state_tst, state_tst.student_code, fixed=True)

def test_student_typed_fixed_subset_pass(state_tst):
    select = check_statement(state_tst, "select", 0)
    where = check_clause(select, "where_clause")
    cf.test_student_typed(where, "id > 4", fixed=True)

def test_student_typed_fixed_subset_fail(state_tst):
    select = check_statement(state_tst, "select", 0)
    where = check_clause(select, "where_clause")
    with pytest.raises(TF):
        cf.test_student_typed(where, "WHERE id > 4", fixed=True)

def test_student_typed_subset_re_pass(state_tst):
    select = check_statement(state_tst, "select", 0)
    where = check_clause(select, "where_clause")
    cf.test_student_typed(where, "id > [0-9]")

def test_student_typed_subset_re_pass(state_tst):
    select = check_statement(state_tst, "select", 0)
    where = check_clause(select, "where_clause")
    with pytest.raises(TF):
        cf.test_student_typed(where, "id > [a-z]")
