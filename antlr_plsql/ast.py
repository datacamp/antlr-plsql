import sys
from ast import AST
from antlr4.tree import Tree
from antlr4.Token import CommonToken
from antlr4.InputStream import InputStream
from antlr4 import FileStream, CommonTokenStream

from .plsqlLexer import plsqlLexer
from .plsqlParser import plsqlParser
from .plsqlVisitor import plsqlVisitor

# AST -------------------------------------------------------------------------
# TODO: Finish Unary+Binary Expr
#       sql_script

def parse(sql_text, start='sql_script', strict=False):
    input_stream = InputStream(sql_text)

    lexer = plsqlLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = plsqlParser(token_stream)
    ast = AstVisitor()     

    if strict:
        error_listener = CustomErrorListener()
        parser.addErrorListener(error_listener)

    return ast.visit(getattr(parser, start)())

from antlr_ast import AstNode

class Unshaped(AstNode):
    _fields = ['arr']

    def __init__(self, ctx, arr=tuple()):
        self.arr = arr
        self._ctx = ctx

class Script(AstNode):
    _fields = ['body']
    _priority = 0

    @classmethod
    def _from_sql_script(cls, visitor, ctx):
        body = []

        for child in ctx.children:
            if not isinstance(child, Tree.TerminalNodeImpl):
                body.append(visitor.visit(child))

        return cls(ctx, body = body)

class SelectStmt(AstNode):
    _fields = ['pref', 'target_list', 'into_clause', 'from_clause', 'where_clause',
               'hierarchical_query_clause', 'group_by_clause', 'model_clause', 
               'for_update_clause', 'order_by_clause', 'limit_clause']

    _priority = 1

class Identifier(AstNode):
    _fields = ['fields']

# TODO
class Star(AstNode):
    _fields = []

class AliasExpr(AstNode):
    _fields = ['expr', 'alias']

class BinaryExpr(AstNode):
    _fields = ['op', 'left', 'right']

class UnaryExpr(AstNode):
    _fields = ['op', 'unary_expression->expr']

# PARSE TREE VISITOR ----------------------------------------------------------

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

        return self.result_to_ast(node, result)

    @staticmethod
    def result_to_ast(node, result):
        if len(result) == 1: return result[0]
        elif len(result) == 0: return None
        elif all(isinstance(res, str) for res in result): return " ".join(result)
        elif all(isinstance(res, AstNode) and not isinstance(res, Unshaped) for res in result): return result
        else: return Unshaped(node, result)

    def defaultResult(self):
        return list()

    def aggregateResult(self, aggregate, nextResult):
        aggregate.append(nextResult)
        return aggregate

    def visitTerminal(self, ctx):
        return ctx.getText()

    def visitSql_script(self, ctx):
        return Script._from_sql_script(self, ctx)

    def visitSubqueryParen(self, ctx):
        return self.visit(ctx.subquery())

    def visitSubqueryCompound(self, ctx):
        # TODO: here we form UNION statements etc into binary expr, but should
        #       use a compound statement as in official ast
        return BinaryExpr._from_fields(self, ctx)

    def visitQuery_block(self, ctx):
        return SelectStmt._from_fields(self, ctx)

    def visitDot_id(self, ctx):
        return Identifier._from_fields(self, ctx)

    def visitStar(self, ctx):
        return Star._from_fields(self, ctx)

    def visitStarTable(self, ctx):
        identifier = self.visit(ctx.dot_id())
        identifier.fields += [self.visit(ctx.star())]
        return identifier

    def visitAlias_expr(self, ctx):
        if ctx.alias:
            return AliasExpr._from_fields(self, ctx)
        else:
            return self.visitChildren(ctx)

    def visitBinaryExpr(self, ctx):
        return BinaryExpr._from_fields(self, ctx)
        
    def visitUnaryExpr(self, ctx):
        return UnaryExpr._from_fields(self, ctx)

    #def visitIs_part(self, ctx):
    #    return ctx

    # many outer label visitors ----------------------------------------------

    # expression conds
    visitIsExpr =     visitBinaryExpr
    #visitInExpr =    visitBinaryExpr
    visitRelExpr =    visitBinaryExpr
    visitMemberExpr = visitBinaryExpr
    visitCursorExpr = visitUnaryExpr
    visitNotExpr =    visitUnaryExpr
    visitAndExpr =    visitBinaryExpr
    visitOrExpr =     visitBinaryExpr


    # simple dropping of tokens -----------------------------------------------
    # Note can't filter out TerminalNodeImpl from some currently as in something like
    # "SELECT a FROM b WHERE 1", the 1 will be a terminal node in where_clause
    def visitWhere_clause(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: n is not ctx.WHERE())

    def visitFrom_clause(self, ctx):
        return  self.visitChildren(ctx, predicate = lambda n: n is not ctx.FROM())

    def visitLimit_clause(self, ctx):
        return  self.visitChildren(ctx, predicate = lambda n: n is not ctx.LIMIT())

    def visitColumn_alias(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: n is not ctx.AS())

    def visitTable_ref_list(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: not isinstance(n, Tree.TerminalNodeImpl))

    def visitGroup_by_clause(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: not isinstance(n, Tree.TerminalNodeImpl))

    def visitOrder_by_clause(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: n is not ctx.ORDER() and n is not ctx.BY())

    # converting case insensitive keywords to lowercase -----------------------

    def visitRegular_id(self, ctx):
        # will be a single terminal node
        return self.visitChildren(ctx).lower()

    visitOver_clause_keyword = visitRegular_id
    visitWithin_or_over_clause_keyword = visitRegular_id

    # removing parentheses ----------------------------------------------------

    @staticmethod
    def _exclude_parens(node):
        return not isinstance(node, Tree.TerminalNodeImpl)

    def visitAtom(self, ctx): 
        return self.visitChildren(ctx, predicate = self._exclude_parens)

    visitParenExpr = visitAtom
    visitParenBinaryExpr = visitAtom

from antlr4.error.ErrorListener import ErrorListener
from antlr4.error.Errors import RecognitionException
class AntlrException(Exception):
    def __init__(self, msg, orig):
        self.msg, self.orig = msg, orig

class CustomErrorListener(ErrorListener):
    def syntaxError(self, recognizer, badSymbol, line, col, msg, e):
        if e is not None:
            msg = "line {line}: {col} {msg}".format(line=line, col=col, msg=msg)
            raise AntlrException(msg, e)
        else:
            raise AntlrException(msg, None)

    #def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
    #    raise Exception("TODO")

    #def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs):
    #    raise Exception("TODO")

    #def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
    #    raise Exception("TODO")
