from pythonwhat import check_syntax as cs
from pythonwhat.check_syntax import Chain
from pythonwhat.Test import TestFail, Test
from sqlwhat.State import State

# TODO: should be defined on chain class, rather than module level in pw
cs.ATTR_SCTS = globals()

def Ex(state=None):
    return Chain(state or State.root_state)

def check_statement(name, index=0, missing_msg="missing statement", state=None):
    pass

def check_clause(index, state=None):
    pass

def check_correct(index, state=None):
    pass

def check_result(msg="Incorrect result.", state=None):
    stu_res = state.student_result
    sol_res = state.solution_result
    if stu_res != sol_res:
        state.reporter.do_test(Test(msg))

    return state

def has_equal_ast(msg="Incorrect AST", state=None):
    if repr(state.student_ast) != repr(state.solution_ast):
        state.reporter.do_test(Test(msg))

    return state

def test_mc(correct, msgs, state=None):
    ctxt = {}
    exec(state.student_code, globals(), ctxt)
    if ctxt['selected_option'] != correct:
        state.reporter.do_test(Test(msgs[correct-1]))

    return state

