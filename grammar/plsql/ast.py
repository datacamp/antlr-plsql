import sys
from antlr4.Token import CommonToken
from antlr4.InputStream import InputStream
from antlr4 import FileStream, CommonTokenStream

from plsqlLexer import plsqlLexer
from plsqlParser import plsqlParser
from plsqlVisitor import plsqlVisitor

# AST -------
# TODO: Unary expressions
#       visitChildren returns Raw node if receives > result
#       _dump method for each node, starting with smallest

class AstNode:
    def __init__(self, ctx, visitor):
        _ctx = ctx

        any_match = False
        for mapping in self._fields:
            k, *name = mapping.split('->')
            if name: k = name[0]

            print(k)
            child = getattr(ctx, k)
            

            if callable(child): child = child()
            elif isinstance(child, CommonToken):
                # giving a name to lexer rules sets it to a token,
                # rather than the terminal node corresponding to that token
                # so we need to find it in children
                child = next(filter(lambda c: getattr(c, 'symbol', None) is child, ctx.children))

            if isinstance(child, list):
                any_match = True
                setattr(self, k, [visitor.visit(el) for el in child])
            elif child:
                any_match = True
                setattr(self, k, visitor.visit(child))
            else:
                setattr(self, k, child)

    def __str__(self):
        els = [k for k in self._fields if getattr(self, k) is not None]
        return "{}: {}".format(self.__class__.__name__, ", ".join(els))

    def __repr__(self):
        field_reps = {k: repr(getattr(self, k)) for k in self._fields}
        args = ", ".join("{} = {}".format(k, v) for k, v in field_reps.items())
        return "{}({})".format(self.__class__.__name__, args)
            

class Unshaped(AstNode):
    _fields = ['arr']

    def __init__(self, ctx, arr=tuple()):
        self.arr = arr
        self._ctx = ctx

class SelectStmt(AstNode):
    _fields = ['pref', 'expr', 'into_clause', 'from_clause', 'where_clause',
               'hierarchical_query_clause', 'group_by_clause', 'model_clause']

class Identifier(AstNode):
    _fields = ['fields']

class Star(AstNode):
    def __init__(self, *args, **kwargs): pass

class AliasExpr(AstNode):
    _fields = ['expr', 'alias']

class BinaryExpr(AstNode):
    _fields = ['op', 'left', 'right']

class UnaryExpr(AstNode):
    _fields = ['op', 'unary_expression->expr']

# VISITOR -----------

class AstVisitor(plsqlVisitor):
    def visitChildren(self, node, predicate=None):
        result = self.defaultResult()
        n = node.getChildCount()
        for i in range(n):
            if not self.shouldVisitNextChild(node, result):
                return

            c = node.getChild(i)
            if predicate and not predicate(c): continue

            childResult = c.accept(self)
            result = self.aggregateResult(result, childResult)

        if len(result) == 1: return result[0]
        elif len(result) == 0: return None
        else: return Unshaped(node, result)

    def defaultResult(self):
        return list()

    def aggregateResult(self, aggregate, nextResult):
        aggregate.append(nextResult)
        return aggregate

    def visitQuery_block(self, ctx):
        return SelectStmt(ctx, self)

    def visitTerminal(self, ctx):
        return ctx.getText()

    def visitDot_id(self, ctx):
        return Identifier(ctx, self)

    def visitStar(self, ctx):
        return Star(ctx, self)

    def visitStarTable(self, ctx):
        # TODO: account for table link with '@'
        identifier = self.visit(ctx.dot_id)
        identifier.fields += Star()
        return identifier

    def visitAlias_expr(self, ctx):
        if ctx.alias:
            return AliasExpr(ctx, self)
        else:
            return self.visitChildren(ctx, predicate=lambda n: n is not ctx.alias)

    def visitExpression(self, ctx):
        

    def visitBinaryExpr(self, ctx):
        return BinaryExpr(ctx, self)
        
    def visitUnaryExpr(self, ctx):
        return UnaryExpr(ctx, self)

    # simple dropping of tokens ------
    
    def visitWhere_clause(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: n is not ctx.WHERE())





input_stream = InputStream("""SELECT DISTINCT id, artists.name as name2 FROM artists WHERE id + 1 AND name || 'greg' """)

lexer = plsqlLexer(input_stream)
token_stream = CommonTokenStream(lexer)
parser = plsqlParser(token_stream)
#tree = parser.sql_script()
ast = AstVisitor()     
select = ast.visit(parser.query_block())
#ctx = ast.visit(parser.dot_id())


