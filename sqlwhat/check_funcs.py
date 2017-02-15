from pythonwhat import check_syntax as cs
from pythonwhat.check_syntax import Chain
from pythonwhat.Test import TestFail, Test
from sqlwhat.State import State
from sqlwhat.selectors import dispatch
from functools import partial

# TODO: should be defined on chain class, rather than module level in pw
cs.ATTR_SCTS = globals()

def Ex(state=None):
    return Chain(state or State.root_state)

def check_statement(name, index=0, missing_msg="missing statement", state=None):
    df = partial(dispatch, 'statement', name, slice(None))

    stu_stmt_list = df(state.student_ast)
    try: stu_stmt = stu_stmt_list[index]
    except IndexError: state.reporter.do_test(Test(missing_msg))

    sol_stmt_list = df(state.solution_ast) 
    try: sol_stmt = sol_stmt_list[index]
    except IndexError: raise IndexError("Can't get %s statement at index %s"%(name, index))

    return state.to_child(student_ast = stu_stmt, solution_ast = sol_stmt)

def check_clause(name, missing_msg="missing clause", state=None):
    try: stu_attr = getattr(state.student_ast, name)
    except: state.reporter.do_test(Test(missing_msg))

    try: sol_attr = getattr(state.solution_ast, name)
    except IndexError: raise IndexError("Can't get %s attribute"%name)

    # fail if attribute exists, but is none only for student
    if stu_attr is None and sol_attr is not None:
        state.reporter.do_test(Test(missing_msg))

    return state.to_child(student_ast = stu_attr, solution_ast = sol_attr)

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

