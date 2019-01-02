from antlr4.tree import Tree

from antlr_ast.ast import (
    parse as parse_ast,
    bind_to_visitor,
    AstNode,
    Speaker,
    AntlrException as ParseError,
)

from . import grammar

# AST -------------------------------------------------------------------------
# TODO: Finish Unary+Binary Expr
#       sql_script


def parse(sql_text, start="sql_script", strict=False):
    tree = parse_ast(grammar, sql_text, start, strict)
    return AstVisitor().visit(tree)


import yaml


def parse_from_yaml(fname):
    data = yaml.load(open(fname)) if isinstance(fname, str) else fname
    out = {}
    for start, cmds in data.items():
        out[start] = [parse(cmd, start) for cmd in cmds]
    return out


class Unshaped(AstNode):
    _fields_spec = ["arr"]

    def __init__(self, ctx, arr=tuple()):
        self.arr = arr
        self._ctx = ctx


class Script(AstNode):
    _fields_spec = ["body"]
    _rules = [("sql_script", "_from_sql_script")]
    _priority = 0

    @classmethod
    def _from_sql_script(cls, visitor, ctx):
        body = []

        for child in ctx.children:
            if not isinstance(child, Tree.TerminalNodeImpl):
                body.append(visitor.visit(child))

        return cls(ctx, body=body)


class SelectStmt(AstNode):
    _fields_spec = [
        "pref",
        "target_list",
        "into_clause",
        "from_clause",
        "where_clause",
        "hierarchical_query_clause",
        "group_by_clause",
        "having_clause",
        "model_clause",
        "for_update_clause",
        "order_by_clause",
        "limit_clause",
        "with_clause",
    ]
    _rules = [
        ("query_block", "_from_query_block"),
        ("select_statement", "_from_select"),
    ]

    _priority = 1

    @classmethod
    def _from_query_block(cls, visitor, ctx):
        # allowing arbitrary order for some clauses, means their results are lists w/single item
        # could also do testing to make sure clauses weren't specified multiple times
        query = cls._from_fields(visitor, ctx)
        unlist_clauses = cls._fields[cls._fields.index("group_by_clause") :]
        for k in unlist_clauses:
            attr = getattr(query, k, [])
            if isinstance(attr, list):
                setattr(query, k, attr[0] if len(attr) else None)

        return query

    @classmethod
    def _from_select(cls, visitor, ctx):
        select = visitor.visit(ctx.subquery())
        with_ctx = ctx.subquery_factoring_clause()
        if with_ctx is not None:
            with_clause = visitor.visit(with_ctx)
            select.with_clause = with_clause
        return select


class Union(AstNode):
    _fields_spec = ["left", "op", "right", "order_by_clause"]
    _rules = [("SubqueryCompound", "_from_subquery_compound")]

    @classmethod
    def _from_subquery_compound(cls, visitor, ctx):
        # hoists up ORDER BY clauses from the right SELECT statement
        # since the final ORDER BY applies to the entire statement (not just subquery)
        union = cls._from_fields(visitor, ctx)
        if not isinstance(ctx.right, grammar.Parser.SubqueryParenContext):
            order_by = getattr(union.right, "order_by_clause", None)
            union.order_by_clause = order_by
            # remove from right SELECT
            if order_by:
                union.right.order_by_clause = None

        return union


class Identifier(AstNode):
    _fields_spec = ["fields"]
    _rules = ["dot_id"]


# TODO
class Star(AstNode):
    _fields_spec = []
    _rules = ["star"]


class TableAliasExpr(AstNode):
    # TODO order_by_clause
    _fields_spec = ["query_name->alias", "column_name_list->alias_columns", "subquery"]
    _rules = ["factoring_element"]


class AliasExpr(AstNode):
    _fields_spec = ["expr", "alias"]
    _rules = [("alias_expr", "_from_alias"), ("TableRefAux", "_from_table_ref")]

    @classmethod
    def _from_alias(cls, visitor, ctx):
        if ctx.alias:
            return cls._from_fields(visitor, ctx)
        else:
            return visitor.visitChildren(ctx)

    @classmethod
    def _from_table_ref(cls, visitor, ctx):
        # TODO flashback_query_clause + table_ref_aux
        # TODO table_ref_aux.pivot_clause
        query = visitor.visit(ctx.table_ref_aux().dml_table_expression_clause())
        alias_ctx = ctx.table_alias()
        if alias_ctx is not None:
            alias = cls(ctx)
            alias.alias = visitor.visit(alias_ctx)
            alias.expr = query
            return alias
        else:
            return query


class BinaryExpr(AstNode):
    _fields_spec = ["left", "op", "right"]
    _rules = [
        "BinaryExpr",
        "IsExpr",
        "RelExpr",
        "MemberExpr",
        "AndExpr",
        "OrExpr",
        ("ModExpr", "_from_mod"),
        ("BetweenExpr", "_from_mod"),
        ("LikeExpr", "_from_mod"),
        ("InExpr", "_from_in_expr"),
    ]

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
    _fields_spec = ["op", "unary_expression->expr"]
    _rules = ["UnaryExpr", "CursorExpr", "NotExpr"]


class OrderByExpr(AstNode):
    _fields_spec = ["order_by_elements->expr"]
    _rules = ["order_by_clause"]


class SortBy(AstNode):
    _fields_spec = ["expression->expr", "direction", "nulls"]
    _rules = ["order_by_elements"]


class JoinExpr(AstNode):
    _fields_spec = [
        "left",
        "join_type",
        "table_ref->right",
        "join_on_part->cond",
        # fields below are Oracle specific
        "join_using_part->using",
        "query_partition_clause",
    ]
    _rules = [("JoinExpr", "_from_table_ref")]

    @classmethod
    def _from_table_ref(cls, visitor, ctx):
        join_expr = cls._from_fields(visitor, ctx.join_clause())
        join_expr._ctx = ctx
        join_expr.left = visitor.visit(ctx.table_ref())

        return join_expr


from collections.abc import Sequence


class Call(AstNode):
    _fields_spec = [
        "name",
        "dot_id->name",
        "pref",
        "args",
        "function_argument->args",
        "function_argument_analytic->args",
        "concatenation->args",
        "over_clause",
    ]
    _rules = [
        ("aggregate_windowed_function", "_from_aggregate_call"),
        ("FuncCall", "_from_func"),
        ("TodoCall", "_from_todo"),
    ]

    @staticmethod
    def get_name(ctx):
        return ctx.children[0].getText().upper()

    @classmethod
    def _from_aggregate_call(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)
        obj.name = cls.get_name(ctx)

        if obj.args is None:
            obj.args = []
        elif not isinstance(obj.args, Sequence):
            obj.args = [obj.args]
        return obj

    @classmethod
    def _from_func(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)
        if hasattr(obj.args, "arr"):
            # args may be Unshaped by non-AstNode argument
            # unpack the array inside:
            obj.args = obj.args.arr
        return obj

    @classmethod
    def _from_todo(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)
        regular_id_ctx = ctx.regular_id()
        if regular_id_ctx is not None:
            obj.component = visitor.visit(regular_id_ctx)
        concatenation_ctx = ctx.concatenation()
        if concatenation_ctx is not None:
            obj.expr = visitor.visit(concatenation_ctx)
        within_or_over_part_ctx = ctx.within_or_over_part()
        if within_or_over_part_ctx is not None:
            for el in within_or_over_part_ctx:
                over_clause_ctx = el.over_clause()
                if over_clause_ctx is not None:
                    obj.over_clause = visitor.visit(over_clause_ctx)
        return obj


class OverClause(AstNode):
    _fields_spec = [
        "query_partition_clause->partition",
        "order_by_clause",
        "windowing_clause",
    ]
    _rules = ["over_clause"]


class Case(AstNode):
    _fields_spec = [
        "simple_case_when_part->switches",
        "searched_case_when_part->switches",
        "case_else_part->else_expr",
    ]
    _rules = ["simple_case_statement", "searched_case_statement"]  # case_statement
    # 'label' in grammar not correct?


class CaseWhen(AstNode):
    _fields_spec = ["whenExpr->when", "thenExpr->then"]
    _rules = ["simple_case_when_part", "searched_case_when_part"]


# class FunctionArgument


# PARSE TREE VISITOR ----------------------------------------------------------


class AstVisitor(grammar.Visitor):
    def visitChildren(self, node, predicate=None):
        result = self.defaultResult()
        n = node.getChildCount()
        for i in range(n):
            if not self.shouldVisitNextChild(node, result):
                return

            c = node.getChild(i)
            if predicate and not predicate(c):
                continue

            childResult = c.accept(self)
            result = self.aggregateResult(result, childResult)

        return self.result_to_ast(node, result)

    @staticmethod
    def result_to_ast(node, result):
        if len(result) == 1:
            return result[0]
        elif len(result) == 0:
            return None
        elif all(isinstance(res, str) for res in result):
            return " ".join(result)
        elif all(
            isinstance(res, AstNode) and not isinstance(res, Unshaped) for res in result
        ):
            return result
        else:
            return Unshaped(node, result)

    def defaultResult(self):
        return list()

    def aggregateResult(self, aggregate, nextResult):
        aggregate.append(nextResult)
        return aggregate

    def visitTerminal(self, ctx):
        """converting case insensitive keywords and identifiers to lowercase"""
        text = ctx.getText()
        quotes = ["'", '"']
        if not (text[0] in quotes and text[-1] in quotes):
            text = text.lower()
        return text

    def visitSubqueryParen(self, ctx):
        return self.visit(ctx.subquery())

    def visitStarTable(self, ctx):
        identifier = self.visit(ctx.dot_id())
        identifier.fields += [self.visit(ctx.star())]
        return identifier

    # function calls -------

    def visitFunction_argument_analytic(self, ctx):
        if not (ctx.respect_or_ignore_nulls() or ctx.keep_clause()):
            return [self.visit(arg) for arg in ctx.argument()]
        else:
            return self.visitChildren(ctx)

    # def visitIs_part(self, ctx):
    #    return ctx

    # simple dropping of tokens -----------------------------------------------
    # Note can't filter out TerminalNodeImpl from some currently as in something like
    # "SELECT a FROM b WHERE 1", the 1 will be a terminal node in where_clause
    def visitWhere_clause(self, ctx):
        return self.visitChildren(ctx, predicate=lambda n: n is not ctx.WHERE())

    def visitLimit_clause(self, ctx):
        return self.visitChildren(ctx, predicate=lambda n: n is not ctx.LIMIT())

    def visitColumn_alias(self, ctx):
        return self.visitChildren(ctx, predicate=lambda n: n is not ctx.AS())

    def visitHaving_clause(self, ctx):
        return self.visitChildren(ctx, predicate=lambda n: n is not ctx.HAVING())

    # TODO similar pattern, reuse?

    def visitExpression_list(self, ctx):
        return [self.visit(expr) for expr in ctx.expression()]
        # return self.visitChildren(ctx, predicate = lambda n: not isinstance(n, Tree.TerminalNode))

    def visitInto_clause(self, ctx):
        return [self.visit(expr) for expr in ctx.variable_name()]

    _remove_terminal = [
        "from_clause",
        "table_ref_list",
        "group_by_clause",
        "join_on_part",
        "join_using_part",
        "atom",
        "ParenExpr",
        "ParenBinaryExpr",
        "case_else_part",
        "table_alias",
        "subquery_factoring_clause",
        "dml_table_expression_clause",
        "function_argument",
        "argument_list",
    ]


# TODO: convert more visitors now visitor generation is fixed
# for some reason can't get this to work as in tsql
# Override visit methods in AstVisitor for all nodes (in _rules) that convert to the AstNode classes
import inspect

for item in list(globals().values()):
    if inspect.isclass(item) and issubclass(item, AstNode):
        if getattr(item, "_rules", None) is not None:
            item._bind_to_visitor(AstVisitor)

# Override node visiting methods to add terminal child skipping in AstVisitor
for rule in AstVisitor._remove_terminal:
    # f = partial(AstVisitor.visitChildren, predicate = lambda n: not isinstance(n, Tree.TerminalNode))
    def skip_terminal_child_nodes(self, ctx):
        return self.visitChildren(
            ctx, predicate=lambda n: not isinstance(n, Tree.TerminalNode)
        )

    bind_to_visitor(AstVisitor, rule, skip_terminal_child_nodes)


import pkg_resources

speaker_cfg = yaml.load(pkg_resources.resource_stream("antlr_plsql", "speaker.yml"))
speaker = Speaker(**speaker_cfg)

if __name__ == "__main__":
    query = """
SELECT id FROM artists WHERE id > 100
    """
    parse(query)
