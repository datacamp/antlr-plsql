from sqlwhat.check_funcs import test_mc as _test_mc, Ex
from sqlwhat.State import State
from pythonwhat.Reporter import Reporter
from pythonwhat.Test import TestFail as TF
import pytest

def prepare_state(student_code):
    return State(
        student_code = student_code,
        reporter = Reporter(),
        # args below should be ignored
        solution_code = "NA", pre_exercise_code = "NA", 
        student_result = [], solution_result = [],
        student_conn = None, solution_conn = None)

def test_mc_alone_pass():
    state = prepare_state("selected_option = 1")
    _test_mc(1, ['good', 'bad'], state=state)

def test_mc_alone_fail():
    state = prepare_state("selected_option = 2")
    with pytest.raises(TF):
        _test_mc(1, ['good', 'bad'], state=state)

def test_mc_chain_pass():
    state = prepare_state("selected_option = 1")
    Ex(state).test_mc(1, ['good', 'bad'])

def test_mc_chain_fail():
    state = prepare_state("selected_option = 2")
    with pytest.raises(TF):
        Ex(state).test_mc(1, ['good', 'bad'])
