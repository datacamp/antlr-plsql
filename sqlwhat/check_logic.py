from pythonwhat.Test import TestFail, Test
from types import GeneratorType
from functools import partial

def fail(state, msg=""):
    """Always fails the SCT, with optional msg."""
    state.reporter.do_test(Test(msg))

    return state

def multi(state, *args):
    """Run multiple subtests. Return original state (for chaining)."""

    rep = state.reporter
    for arg in args:
        # when input is a single test, make iterable
        if callable(arg): arg = [arg]

        for test in arg:
            # assume test is function needing a state argument
            # partial state so reporter can test
            closure = partial(test, state)
            rep.do_test(closure, "")

    # return original state, so can be chained
    return state

def test_or(state, *tests):
    """Test whether at least one SCT passes."""

    rep = state.reporter

    success = False
    first_feedback = None
    for test in tests: 
        try: 
            multi(state, test)
            success = True
        except TestFail as e:
            if not first_feedback: first_feedback = rep.feedback
            rep.failed_test = False

        if success: 
            return
    
    rep.failed_test = True
    rep.feedback = first_feedback
    raise TestFail

def test_correct(state, check, diagnose):
    """Allows feedback from a diagnostic SCT, only if a check SCT fails. 
    
    """
    rep = state.reporter

    def diagnose_and_check(state):
        # use multi twice, since diagnose and check may be lists of tests
        multi(state, diagnose, check)

    test_or(state, diagnose_and_check, check)
