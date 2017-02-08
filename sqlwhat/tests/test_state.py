from sqlwhat import check_funcs
from sqlwhat.State import State
from pythonwhat.Reporter import Reporter
from pythonwhat.Test import TestFail as TF
import pytest

def test_pass():
    state = State(
        student_code = "SELECT * FROM company",
        solution_code = "SELECT * FROM company",
        pre_exercise_code = "",
        student_result = [['id', 'name'], [1, 'greg']],
        solution_result = [['id', 'name'], [1, 'greg']],
        student_conn = None,
        solution_conn = None,
        reporter= Reporter())

    State.root_state = state

    assert check_funcs.Ex().check_result()

def test_fail():
    state = State(
        student_code = "SELECT * FROM company",
        solution_code = "SELECT * FROM company",
        pre_exercise_code = "",
        student_result = [['id', 'name'], [1, 'greg']],
        solution_result = [['id', 'name'], [0, 'greg']],
        student_conn = None,
        solution_conn = None,
        reporter= Reporter())

    State.root_state = state

    with pytest.raises(TF):
        check_funcs.Ex().check_result()
