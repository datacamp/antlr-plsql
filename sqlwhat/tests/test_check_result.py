import pytest
from sqlwhat.State import State
from sqlwhat import check_result as cr
from pythonwhat.Reporter import Reporter
from pythonwhat.Test import TestFail as TF

def prepare_state(sol_result, stu_result):
    return State(
        student_code = "",
        solution_code = "",
        reporter = Reporter(),
        # args below should be ignored
        pre_exercise_code = "NA", 
        student_result = stu_result, solution_result = sol_result,
        student_conn = None, solution_conn = None)

def test_test_has_columns_fail():
    state = prepare_state({'a': [1,2,3]}, {})
    with pytest.raises(TF): cr.test_has_columns(state)

def test_test_has_columns_pass_no_rows():
    state = prepare_state({'a': [1,2,3]}, {'a': []})
    cr.test_has_columns(state)

def test_test_nrows_fail():
    state = prepare_state({'a': [1,2,3]}, {'b': [1,2]})
    with pytest.raises(TF): cr.test_nrows(state)

def test_test_ncols_pass():
    state = prepare_state({'a': [1,2,3]}, {'b': [1,2,3]})
    cr.test_nrows(state)

def test_test_ncols_fail():
    state = prepare_state({'a': [1], 'b': [1]}, {'c': [1]})
    with pytest.raises(TF): cr.test_ncols(state)

def test_test_ncols_pass():
    state = prepare_state({'a': [1], 'b': [1]}, {'c': [1], 'd': [1]})
    cr.test_ncols(state)

@pytest.mark.parametrize('match, stu_result', [
    [ 'any', {'b': [1]} ],
    [ 'any', {'b': [1], 'a': [2]} ],
    [ 'exact', {'a': [1]} ]
    ])
def test_test_column_pass(match, stu_result):
    state = prepare_state({'a': [1]}, stu_result)
    cr.test_column(state, 'a', match=match)

@pytest.mark.parametrize('match, stu_result', [
    ( 'any', {'a': [2]} ),
    ( 'exact', {'b': [1], 'a': [2]} )
    ])
def test_test_column_fail(match, stu_result):
    state = prepare_state({'a': [1]}, stu_result)
    with pytest.raises(TF): cr.test_column(state, 'a', match=match)
