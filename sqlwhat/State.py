from sqlwhat.grammar.plsql import ast
from copy import copy
import inspect

class State:
    def __init__(self,
                 student_code,
                 solution_code,
                 pre_exercise_code,
                 student_conn,
                 solution_conn,
                 student_result,
                 solution_result,
                 reporter,
                 solution_ast = None,
                 student_ast = None):

        for k,v in locals().items():
            if k != 'self': setattr(self, k, v)

        self.student_ast  = ast.parse(student_code)  if student_ast  is None else student_ast
        self.solution_ast = ast.parse(solution_code) if solution_ast is None else solution_ast

    def to_child(self, **kwargs):
        """Basic implementation of returning a child state"""

        good_pars = inspect.signature(self.__init__).parameters
        bad_pars = set(kwargs) - set(good_pars)
        if bad_pars:
            raise KeyError("Invalid init params for State: %s"% ", ".join(bad_pars))

        child = copy(self)
        for k, v in kwargs.items(): setattr(child, k, v)
        child.parent = self
        return child
