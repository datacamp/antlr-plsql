from pythonwhat import check_syntax as cs
from pythonwhat.Test import TestFail, Test

from sqlwhat.State import State
from sqlwhat.selectors import dispatch, ast
from sqlwhat.check_result import check_result, test_has_columns, test_nrows, test_ncols, test_column
from sqlwhat.check_logic import fail, multi, test_or, test_correct

from functools import partial
import copy

# TODO: should be defined on chain class, rather than module level in pw
ATTR_SCTS = globals()

class Chain:
    def __init__(self, state):
        self._state = state
        self._crnt_sct = None
        self._waiting_on_call = False

    def __getattr__(self, attr):
        if attr not in ATTR_SCTS: raise AttributeError("No SCT named %s"%attr)
        elif self._waiting_on_call: 
            raise AttributeError("Did you forget to call a statement? "
                                 "e.g. Ex().check_list_comp.check_body()")
        else:
            # make a copy to return, 
            # in case someone does: a = chain.a; b = chain.b
            chain = copy.copy(self)
            chain._crnt_sct = ATTR_SCTS[attr]
            chain._waiting_on_call = True
            return chain

    def __call__(self, *args, **kwargs):
        # NOTE: the only change from python what is that state is now 1st pos arg below
        self._state = self._crnt_sct(self._state, *args, **kwargs)
        self._waiting_on_call = False
        return self

def Ex(state=None):
    """Returns the current code state as a Chain instance.
    
    This allows SCTs to be run without including their 1st argument, ``state``.

    :Example:
        
    """
    return Chain(state or State.root_state)


def check_statement(state, name, index=0, missing_msg="missing statement"):
    """Select a node from abstract syntax tree (AST), using its name and index position.
    
    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        name : the name of the abstract syntax tree node to find.
        index: the position of that node (see below for details).
        missing_msg: feedback message if node is not in student AST.

    :Example:
        If both the student and solution code are.. ::

            SELECT a FROM b; SELECT x FROM y;

        then we can focus on the first select with::
        
            # approach 1: with manually created State instance
            state = State(*args, **kwargs)
            new_state = check_statement(state, 'select', 0)
            
            # approach 2:  with Ex and chaining
            new_state = Ex().check_statement('select', 0)

    """
    df = partial(dispatch, 'statement', name, slice(None))

    stu_stmt_list = df(state.student_ast)
    try: stu_stmt = stu_stmt_list[index]
    except IndexError: state.reporter.do_test(Test(missing_msg))

    sol_stmt_list = df(state.solution_ast) 
    try: sol_stmt = sol_stmt_list[index]
    except IndexError: raise IndexError("Can't get %s statement at index %s"%(name, index))

    return state.to_child(student_ast = stu_stmt, solution_ast = sol_stmt)


def check_clause(state, name, missing_msg="missing clause"):
    """Select an attribute from an abstract syntax tree (AST) node, using the attribute name.
    
    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        name: the name of the attribute to select from current AST node.
        missing_msg: feedback message if attribute is not in student AST.

    :Example:
        If both the student and solution code are.. ::
            
            SELECT a FROM b; SELECT x FROM y;

        then we can get the from_clause using::
            # approach 1: with manually created State instance -----
            state = State(*args, **kwargs)
            select = check_statement(state, 'select', 0)
            clause = check_clause(select, 'from_clause')

            # approach 2: with Ex and chaining ---------------------
            select = Ex().check_statement('select', 0)     # get first select statement
            clause = select.check_clause('from_clause')    # get from_clause
    """
    try: stu_attr = getattr(state.student_ast, name)
    except: state.reporter.do_test(Test(missing_msg))

    try: sol_attr = getattr(state.solution_ast, name)
    except IndexError: raise IndexError("Can't get %s attribute"%name)

    # fail if attribute exists, but is none only for student
    if stu_attr is None and sol_attr is not None:
        state.reporter.do_test(Test(missing_msg))

    return state.to_child(student_ast = stu_attr, solution_ast = sol_attr)

import re

def test_student_typed(state, text, msg="Solution does not contain {}.", fixed=False):
    """Test whether the student code contains text.

    Args:
        state: State instance describing student and solution code. Can be omitted if used with Ex().
        text : text that student code must contain.
        msg  : feedback message if text is not in student code.
        fixed: whether to match text exactly, rather than using regular expressions.

    :Example:
        If the student code is.. ::

            SELECT a FROM b WHERE id < 100

        Then the first test below would (unfortunately) pass, but the second would fail..::

            # contained in student code
            Ex().test_student_typed(test="id < 10")

            # the $ means that you are matching the end of a line
            Ex().test_student_typed(test="id < 10$")

        By setting ``fixed = True``, you can search for fixed strings::

            # without fixed = True, '*' matches any character
            Ex().test_student_typed(test="SELECT * FROM b")               # passes
            Ex().test_student_typed(test="SELECT \\* FROM b")             # fails
            Ex().test_student_typed(test="SELECT * FROM b", fixed=True)   # fails


    """
    stu_text = state.student_ast._get_text(state.student_code)

    _msg = msg.format(text)
    if fixed and not text in stu_text:            # simple text matching
        state.reporter.do_test(Test(msg))
    elif not re.match(text, stu_text):            # regex
        state.reporter.do_test(Test(msg))

    return state


def has_equal_ast(state, msg="Incorrect AST", sql=None, start="sql_script"):
    """Test whether the student and solution code have identical AST representations
    
    """
    sol_ast = state.solution_ast if sql is None else ast.parse(sql, start)
    if repr(state.student_ast) != repr(sol_ast):
        state.reporter.do_test(Test(msg))

    return state


def test_mc(state, correct, msgs):
    ctxt = {}
    exec(state.student_code, globals(), ctxt)
    if ctxt['selected_option'] != correct:
        state.reporter.do_test(Test(msgs[correct-1]))

    return state

