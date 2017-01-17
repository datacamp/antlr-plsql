from pythonwhat import check_syntax as cs
from pythonwhat.check_syntax import Chain
from pythonwhat.Test import TestFail, Test
from sqlwhat.State import State

# TODO: should be defined on chain class, rather than module level in pw
cs.ATTR_SCTS = globals()

def Ex():
    return Chain(State.root_state)

def check_statement(index, state=None):
    pass

def check_clause(index, state=None):
    pass

def check_correct(index, state=None):
    pass

def check_result(msg="Incorrect result.", state=None):
    stu_res = state.student_process.getLastQueryResult()
    sol_res = state.solution_process.getLastQueryResult()
    if stu_res != sol_res:
        state.reporter.do_test(Test(msg))
