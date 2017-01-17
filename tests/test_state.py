from sqlwhat import check_funcs
from sqlwhat.State import State
from pythonwhat.Reporter import Reporter
from pythonwhat.Test import TestFail as TF
from helper import MockProcess
import pytest

def test_pass():
    state = State(
        student_code = "SELECT * FROM company",
        solution_code = "SELECT * FROM company",
        pre_exercise_code = "",
        student_process = MockProcess([['id', 'name'], [1, 'greg']]),
        solution_process = MockProcess([['id', 'name'], [1, 'greg']]),
        raw_student_output = "TODO",
        reporter= Reporter())

    State.root_state = state

    assert check_funcs.Ex().check_result()

def test_fail():
    state = State(
        student_code = "SELECT * FROM company",
        solution_code = "SELECT * FROM company",
        pre_exercise_code = "",
        student_process = MockProcess([['id', 'name'], [1, 'greg']]),
        solution_process = MockProcess([['id', 'name'], [0, 'greg']]),
        raw_student_output = "TODO",
        reporter= Reporter())

    State.root_state = state

    with pytest.raises(TF):
        check_funcs.Ex().check_result()
