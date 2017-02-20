import pytest
from sqlwhat.State import State
from sqlwhat import check_logic as cl
from pythonwhat.Reporter import Reporter
from pythonwhat.Test import TestFail as TF
from functools import partial

@pytest.fixture(scope="function")
def state():
    return State(
        student_code = "",
        solution_code = "",
        reporter = Reporter(),
        # args below should be ignored
        pre_exercise_code = "NA", 
        student_result = {'a': [1]}, solution_result = {'b': [2]},
        student_conn = None, solution_conn = None)

def fails(state, msg=""): 
    state.reporter.feedback.msg = msg
    raise TF

def passes(state): return state

@pytest.mark.parametrize('arg1', ( passes, [passes, passes] ))
@pytest.mark.parametrize('arg2', ( passes, [passes, passes] ))
def test_test_multi_pass_one(state, arg1, arg2):
    cl.multi(state, arg1, arg2)

@pytest.mark.parametrize('arg1', ( fails, [passes, fails] ))
def test_test_multi_fail_arg1(state, arg1):
    with pytest.raises(TF): cl.multi(state, arg1)

@pytest.mark.parametrize('arg2', ( fails, [passes, fails] ))
def test_test_multi_fail_arg2(state, arg2):
    with pytest.raises(TF): cl.multi(state, passes, arg2)

def test_test_or_pass(state):
    cl.test_or(state, passes, fails)

def test_test_or_fail(state):
    with pytest.raises(TF): cl.test_or(state, fails, fails)

def test_test_correct_pass(state):
    cl.test_correct(state, passes, fails)

def test_test_correct_fail_msg(state):
    f1, f2 = partial(fails, msg="f1"), partial(fails, msg="f2")
    with pytest.raises(TF): 
        cl.test_correct(state, f1, f2)
        assert state.reporter.feedback.message == "f2"

def test_test_correct_fail_multi_msg(state):
    f1, f2, f3 = [partial(fails, msg="f%s"%ii) for ii in range(1, 4)]
    with pytest.raises(TF): 
        cl.test_correct(state, [f1, f3], [f2, f3])
        assert state.reporter.feedback.message == "f2"
