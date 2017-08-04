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
        parser.removeErrorListeners()
        parser.addErrorListener(error_listener)

    return ast.visit(getattr(parser, start)())

import yaml
def parse_from_yaml(fname):
    data = yaml.load(open(fname)) if isinstance(fname, str) else fname
    out = {}
    for start, cmds in data.items():
        out[start] = [parse(cmd, start) for cmd in cmds]
    return out

from antlr_ast import AstNode, Speaker

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
               'hierarchical_query_clause', 'group_by_clause', 'having_clause', 'model_clause', 
               'for_update_clause', 'order_by_clause', 'limit_clause']

    _priority = 1

    @classmethod
    def _from_query_block(cls, visitor, ctx):
        # allowing arbitrary order for some clauses, means their results are lists w/single item
        # could also do testing to make sure clauses weren't specified multiple times
        query = cls._from_fields(visitor, ctx)
        unlist_clauses = cls._fields[cls._fields.index('group_by_clause'): ]
        for k in unlist_clauses:
            attr = getattr(query, k, [])
            if isinstance(attr, list):
                setattr(query, k, attr[0] if len(attr) else None)

        return query

class Union(AstNode):
    _fields = ['left', 'op', 'right', 'order_by_clause']        

    @classmethod
    def _from_subquery_compound(cls, visitor, ctx):
        # hoists up ORDER BY clauses from the right SELECT statement
        # since the final ORDER BY applies to the entire statement (not just subquery)
        union = cls._from_fields(visitor, ctx)
        if not isinstance(ctx.right, plsqlParser.SubqueryParenContext):
            order_by = getattr(union.right, 'order_by_clause', None)
            union.order_by_clause = order_by
            # remove from right SELECT
            if order_by: union.right.order_by_clause = None

        return union

class Identifier(AstNode):
    _fields = ['fields']

# TODO
class Star(AstNode):
    _fields = []

class AliasExpr(AstNode):
    _fields = ['expr', 'alias']

class BinaryExpr(AstNode):
    _fields = ['left', 'op', 'right']
    _rules = ['IsExpr', 'InExpr', 'BetweenExpr', 'LikeExpr', 'RelExpr', 
              'MemberExpr', 'AndExpr', 'OrExpr']

    @classmethod
    def _from_mod(cls, visitor, ctx):
        bin_expr = cls._from_fields(visitor, ctx)
        ctx_not = ctx.NOT()
        if ctx_not:
            return UnaryExpr(ctx, op=visitor.visit(ctx_not), expr=bin_expr)

        return bin_expr

    @classmethod
    def _from_in_expr(cls, visitor, ctx):
        # NOT IN produces unary expression
        bin_or_unary = cls._from_mod(visitor, ctx)
        right = visitor.visit(ctx.subquery() or ctx.expression_list())
        if isinstance(bin_or_unary, UnaryExpr): 
            bin_or_unary.expr.right = right
        else:
            bin_or_unary.right = right
        return bin_or_unary

class UnaryExpr(AstNode):
    _fields = ['op', 'unary_expression->expr']

class OrderByExpr(AstNode):
    _fields = ['order_by_elements->expr']
    #_rules = ['order_by_clause']

class SortBy(AstNode):
    _fields = ['expression->expr', 'direction', 'nulls']
    #_rules = ['order_by_elements']

class JoinExpr(AstNode):
    _fields = ['left', 'join_type', 'table_ref->right',
               'join_on_part->cond', 
               # fields below are Oracle specific
               'join_using_part->using', 'query_partition_clause']

    @classmethod
    def _from_table_ref(cls, visitor, ctx):
        join_expr = cls._from_fields(visitor, ctx.join_clause())
        join_expr._ctx = ctx
        join_expr.left = visitor.visit(ctx.table_ref())

        return join_expr

from collections.abc import Sequence
class Call(AstNode):
    _fields = ['name', 'pref', 'args', 'function_argument_analytic->args', 'concatenation->args', 'over_clause']

    @staticmethod
    def get_name(ctx): return ctx.children[0].getText().upper()

    @classmethod
    def _from_aggregate_call(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)
        obj.name = cls.get_name(ctx)
        
        if obj.args is None: obj.args = []
        elif not isinstance(obj.args, Sequence): obj.args = [obj.args]
        return obj


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
        return Union._from_subquery_compound(self, ctx)

    def visitQuery_block(self, ctx):
        return SelectStmt._from_query_block(self, ctx)

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
    
    def visitOrder_by_clause(self, ctx):
        return OrderByExpr._from_fields(self, ctx)

    def visitOrder_by_elements(self, ctx):
        return SortBy._from_fields(self, ctx)

    def visitBinaryExpr(self, ctx):
        return BinaryExpr._from_fields(self, ctx)

    def visitUnaryExpr(self, ctx):
        return UnaryExpr._from_fields(self, ctx)

    def visitModExpr(self, ctx):
        return BinaryExpr._from_mod(self, ctx)

    def visitJoinExpr(self, ctx):
        return JoinExpr._from_table_ref(self, ctx)

    # function calls -------
    def visitAggregate_windowed_function(self, ctx):
        return Call._from_aggregate_call(self, ctx)

    def visitFunction_argument_analytic(self, ctx):
        if not (ctx.respect_or_ignore_nulls() or ctx.keep_clause()):
            return [self.visit(arg) for arg in ctx.argument()]
        else:
            return self.visitChildren(ctx)

    #def visitIs_part(self, ctx):
    #    return ctx

    # many outer label visitors ----------------------------------------------

    # expression conds
    # TODO replace with for loop over AST classes
    def visitInExpr(self, ctx):
        return BinaryExpr._from_in_expr(self, ctx)

    visitIsExpr =     visitBinaryExpr
    visitBetweenExpr = visitModExpr
    visitLikeExpr = visitModExpr
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
        return  self.visitChildren(ctx, predicate = lambda n: not isinstance(n, Tree.TerminalNode))

    def visitLimit_clause(self, ctx):
        return  self.visitChildren(ctx, predicate = lambda n: n is not ctx.LIMIT())

    def visitColumn_alias(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: n is not ctx.AS())

    def visitTable_ref_list(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: not isinstance(n, Tree.TerminalNodeImpl))

    def visitGroup_by_clause(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: not isinstance(n, Tree.TerminalNodeImpl))

    def visitHaving_clause(self, ctx):
        return  self.visitChildren(ctx, predicate = lambda n: n is not ctx.HAVING())

    def visitExpression_list(self, ctx):
        return [self.visit(expr) for expr in ctx.expression()]
        #return self.visitChildren(ctx, predicate = lambda n: not isinstance(n, Tree.TerminalNode))

    def visitInto_clause(self, ctx):
        return [self.visit(expr) for expr in ctx.variable_name()]

    def visitJoin_on_part(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: not isinstance(n, Tree.TerminalNode))

    def visitJoin_using_part(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: not isinstance(n, Tree.TerminalNode))


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

# TODO: for some reason can't get this to work as in tsql
#import inspect
#for item in list(globals().values()):
#    if inspect.isclass(item) and issubclass(item, AstNode):
#        item._bind_to_visitor(AstVisitor)


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

    def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
        return
        #raise Exception("TODO")

    def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex, conflictingAlts, configs):
        return
        #raise Exception("TODO")

    def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
        return
        #raise Exception("TODO")

import pkg_resources
speaker_cfg = yaml.load(pkg_resources.resource_stream('antlr_plsql', 'speaker.yml'))
speaker = Speaker(**speaker_cfg)
