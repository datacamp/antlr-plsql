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
#       _dump method for each node, starting with smallest

def parse(sql_text, start='sql_script'):
    input_stream = InputStream(sql_text)

    lexer = plsqlLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = plsqlParser(token_stream)
    ast = AstVisitor()     
    # TODO: may also want to construct ast from expression
    return ast.visit(getattr(parser, start)())



class AstNode(AST):         # AST is subclassed only so we can use ast.NodeVisitor...
    _fields = []            # contains child nodes to visit
    _priority = 1           # whether to descend for selection (greater descends into lower)

    # default visiting behavior, which uses fields
    def __init__(self, ctx, visitor):
        self._ctx = ctx

        for mapping in self._fields:
            # parse mapping for -> and indices [] -----
            k, *name = mapping.split('->')
            name = k if not name else name[0]

            # get node -----
            #print(k)
            child = getattr(ctx, k, getattr(ctx, name, None))
            # when not alias needs to be called
            if callable(child): child = child()
            # when alias set on token, need to go from CommonToken -> Terminal Node
            elif isinstance(child, CommonToken):
                # giving a name to lexer rules sets it to a token,
                # rather than the terminal node corresponding to that token
                # so we need to find it in children
                child = next(filter(lambda c: getattr(c, 'symbol', None) is child, ctx.children))

            # set attr -----
            if isinstance(child, list):
                setattr(self, name, [visitor.visit(el) for el in child])
            elif child:
                setattr(self, name, visitor.visit(child))
            else:
                setattr(self, name, child)

    def _get_field_names(self):
        return [el.split('->')[-1] for el in self._fields]

    def _get_text(self, text):
        return text[self._ctx.start.start: self._ctx.stop.stop + 1]

    def __str__(self):
        els = [k for k in self._get_field_names() if getattr(self, k) is not None]
        return "{}: {}".format(self.__class__.__name__, ", ".join(els))

    def __repr__(self):
        field_reps = {k: repr(getattr(self, k)) for k in self._get_field_names() if getattr(self, k) is not None}
        args = ", ".join("{} = {}".format(k, v) for k, v in field_reps.items())
        return "{}({})".format(self.__class__.__name__, args)
            

class Unshaped(AstNode):
    _fields = ['arr']

    def __init__(self, ctx, arr=tuple()):
        self.arr = arr
        self._ctx = ctx

class Script(AstNode):
    _fields = ['body']
    _priority = 0

    def __init__(self, ctx, visitor):
        self._ctx = ctx
        self.body = [visitor.visit(child) for child in ctx.children
                                if not isinstance(child, Tree.TerminalNodeImpl)] # filter semi colons

class SelectStmt(AstNode):
    _fields = ['pref', 'target_list', 'into_clause', 'from_clause', 'where_clause',
               'hierarchical_query_clause', 'group_by_clause', 'model_clause', 
               'for_update_clause', 'order_by_clause', 'limit_clause']

    _priority = 1

class Identifier(AstNode):
    _fields = ['fields']

class Star(AstNode):
    def __init__(self, ctx, *args, **kwargs): self._ctx = ctx

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

        if len(result) == 1: return result[0]
        elif len(result) == 0: return None
        elif all(isinstance(res, str) for res in result): return " ".join(result)
        else: return Unshaped(node, result)

    def defaultResult(self):
        return list()

    def aggregateResult(self, aggregate, nextResult):
        aggregate.append(nextResult)
        return aggregate

    def visitTerminal(self, ctx):
        return ctx.getText()

    def visitSql_script(self, ctx):
        return Script(ctx, self)

    def visitQuery_block(self, ctx):
        return SelectStmt(ctx, self)

    def visitDot_id(self, ctx):
        return Identifier(ctx, self)

    def visitStar(self, ctx):
        return Star(ctx, self)

    def visitStarTable(self, ctx):
        identifier = self.visit(ctx.dot_id())
        identifier.fields += [self.visit(ctx.star())]
        return identifier

    def visitAlias_expr(self, ctx):
        if ctx.alias:
            return AliasExpr(ctx, self)
        else:
            return self.visitChildren(ctx)

    def visitBinaryExpr(self, ctx):
        return BinaryExpr(ctx, self)
        
    def visitUnaryExpr(self, ctx):
        return UnaryExpr(ctx, self)

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
    def visitWhere_clause(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: n is not ctx.WHERE())

    def visitFrom_clause(self, ctx):
        return  self.visitChildren(ctx, predicate = lambda n: n is not ctx.FROM())

    def visitLimit_clause(self, ctx):
        return  self.visitChildren(ctx, predicate = lambda n: n is not ctx.LIMIT())

    def visitColumn_alias(self, ctx):
        return self.visitChildren(ctx, predicate = lambda n: n is not ctx.AS())

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







if __name__ == '__main__':
    # for testing during development
    input_stream = InputStream("""SELECT DISTINCT CURSOR (SELECT id FROM artists), artists.name as name2 FROM artists WHERE id + 1 AND name || 'greg' """)

    lexer = plsqlLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = plsqlParser(token_stream)
    #tree = parser.sql_script()
    ast = AstVisitor()     
    select = ast.visit(parser.sql_script())
    #ctx = ast.visit(parser.dot_id())


