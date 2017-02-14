from sqlwhat.grammar.plsql import ast
from ast import NodeVisitor
from collections.abc import Sequence

class Selector(NodeVisitor):

    def __init__(self, src, priority = None):
        self.src = src
        self.priority = src._priority if priority is None else priority
        self.out = []

    def visit(self, node):
        if self.is_match(node): self.out.append(node)
        if self.has_priority_over(node):
            return super().visit(node)

    def is_match(self, node):
        if type(node) is self.src: return True
        else: return False

    def has_priority_over(self, node):
        return self.priority > node._priority

class Dispatcher:
    def __init__(self, nodes, rules):
        self._types = {}
        for name, funcs in rules.items():
            pred, map_name = funcs if len(funcs) == 2 else funcs + None

            self._types[name] = self.get(nodes, pred, map_name)

    def __call__(self, check, name, index, node):
        # TODO: gentle error handling
        ast_cls = self._types[check][name]

        selector = Selector(ast_cls)
        selector.visit(node)

        return selector.out[index]

    @staticmethod
    def get(nodes, predicate, map_name = lambda x: x):
        return {map_name(k): v for k, v in nodes.items() if predicate(k, v)}

    def __getattr__(self, x):
        return self._types[x]


import inspect
ast_nodes = {k: v for k, v in vars(ast).items() if (inspect.isclass(v) and issubclass(v, ast.AstNode))}

rules = {
        "statement":     [lambda k, v: "Stmt" in k,     lambda k: k.replace("Stmt", "").lower()],
        "other":         [lambda k, v: "Stmt" not in k, lambda k: k.lower()]
        }

dispatch = Dispatcher(ast_nodes, rules)
