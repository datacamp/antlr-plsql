import copy

from antlr4.tree import Tree

from antlr_ast.ast import (
    parse as parse_ast,
    bind_to_visitor,
    AstNode,
    Speaker,
    AntlrException as ParseError,  # noinspection PyUnresolvedReferences
)

from . import grammar

# AST -------------------------------------------------------------------------
# TODO: Finish Unary+Binary Expr
#       sql_script

DEBUG = False


def parse(sql_text, start="sql_script", strict=False):
    tree = parse_ast(grammar, sql_text, start, strict)
    return AstVisitor().visit(tree)


import yaml


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
        "within_clause",
        "over_clause",
    ]
    _rules = [
        ("aggregate_windowed_function", "_from_aggregate_call"),
        ("ExtractCall", "_from_extract"),
        ("FuncCall", "_from_func"),
        ("WithinOrOverCall", "_from_within"),
        ("string_function", "_from_str_func"),
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
    def _from_extract(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)

        regular_id_ctx = ctx.regular_id()
        obj.component = visitor.visit(regular_id_ctx)

        concatenation_ctx = ctx.concatenation()
        obj.expr = visitor.visit(concatenation_ctx)

        return obj

    @classmethod
    def _from_func(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)
        if hasattr(obj.args, "arr"):
            # TODO: look at simplify option
            # args may be Unshaped by non-AstNode argument in visit of function_argument
            # unpack the array inside:
            obj.args = obj.args.arr
        return obj

    @classmethod
    def _from_within(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)

        within_or_over_part_ctx = ctx.within_or_over_part()
        if within_or_over_part_ctx is not None:
            # works only for one such clause
            # TODO: convention for fields where multiple possible
            # >1 (>0): always, mostly, sometimes, exceptionally?
            for el in within_or_over_part_ctx:
                within_clause_ctx = el.order_by_clause()
                if within_clause_ctx is not None:
                    obj.within_clause = visitor.visit(within_clause_ctx)
                over_clause_ctx = el.over_clause()
                if over_clause_ctx is not None:
                    obj.over_clause = visitor.visit(over_clause_ctx)

        return obj

    @classmethod
    def _from_str_func(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)
        obj.args = visitor.visitChildren(ctx, predicate=is_terminal, simplify=False)  # TODO .arr
        return obj


class Cast(AstNode):
    _rules = ["CastCall"]
    _fields_spec = [
        "type_spec->type",
        "subquery->statement",
        "concatenation->statement",
        "expression->statement",
        "atom->statement",
    ]


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


class PartitionBy(AstNode):
    _rules = ["query_partition_clause"]
    _fields_spec = ["expression"]


class RenameColumn(AstNode):
    _rules = ["rename_column_clause"]
    _fields_spec = ["old_column_name->old_name", "new_column_name->new_name"]


class Column(AstNode):
    _rules = ["column_definition"]
    _fields_spec = [
        "column_name->name",
        "datatype->data_type",
        "type_name->data_type",
        "inline_constraint->constraints",
    ]


class AddColumns(AstNode):
    _rules = ["add_column_clause"]
    _fields_spec = ["column_definition->columns"]


class DropColumn(AstNode):
    _rules = ["drop_column_clause"]
    _fields_spec = ["names"]


class AlterColumn(AstNode):
    _rules = ["alter_column_clause"]
    _fields_spec = ["column_name->name", "op", "datatype->data_type", "expression"]


class DropConstraint(AstNode):
    _rules = ["drop_constraint_clause"]
    _fields_spec = ["drop_primary_key_or_unique_or_generic_clause->name"]


class Reference(AstNode):
    _rules = [("references_clause", "_from_references")]
    _fields_spec = ["tableview_name->table", "columns"]

    @classmethod
    def _from_references(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)
        obj.columns = visitor.visitChildren(
            ctx.paren_column_list().column_list(), predicate=is_terminal, simplify=False
        )
        return obj


class CreateTable(AstNode):
    _rules = [("create_table", "_from_table")]
    _fields_spec = [
        "tableview_name->name",
        "TEMPORARY->temporary",
        "select_statement->query",
        "columns",
    ]

    @classmethod
    def _from_table(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)

        relational_properties_ctx = ctx.relational_table().relational_properties()
        if relational_properties_ctx:
            obj.columns = visitor.visitChildren(
                relational_properties_ctx, predicate=is_terminal, simplify=False
            )
        return obj


class AlterTable(AstNode):
    _rules = ["alter_table"]
    _fields_spec = [
        "tableview_name->name",
        "column_clauses->changes",
        "constraint_clauses->changes",
    ]


class AddConstraints(AstNode):
    _fields_spec = ["out_of_line_constraint->constraints"]


class DropConstraints(AstNode):
    _fields_spec = ["constraints"]

    @classmethod
    def _from_drop(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)

        drop_contstraint_clauses_ctx = ctx.drop_constraint_clause()
        obj.constraints = [
            visitor.visit(
                drop.drop_primary_key_or_unique_or_generic_clause().constraint_name()
            )
            for drop in drop_contstraint_clauses_ctx
        ]

        return obj


class DropTable(AstNode):
    _rules = [("drop_table", "_from_table")]
    _fields_spec = ["tableview_name->name", "existence_check"]

    @classmethod
    def _from_table(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)

        if ctx.IF() and ctx.EXISTS():
            obj.existence_check = "if exists"
        return obj


class Constraint(AstNode):
    _rules = [("out_of_line_constraint", "_from_constraint")]
    _fields_spec = [
        "constraint_name->name",
        "type",
        "column_name->columns",
        "reference",
    ]

    @classmethod
    def _from_constraint(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)

        foreign_key_ctx = ctx.foreign_key_clause()
        if ctx.UNIQUE():
            obj.type = "unique"
        elif ctx.PRIMARY() and ctx.KEY():
            obj.type = "primary_key"  # TODO: format?
        elif foreign_key_ctx and foreign_key_ctx.FOREIGN() and foreign_key_ctx.KEY():
            obj.type = "foreign_key"
            columns_ctx = foreign_key_ctx.paren_column_list().column_list()
            obj.columns = visitor.visitChildren(
                columns_ctx, predicate=is_terminal, simplify=False
            )
            reference_ctx = foreign_key_ctx.references_clause()
            obj.reference = visitor.visit(reference_ctx)
        elif ctx.CHECK():
            obj.type = "check"
        return obj


class InsertStmt(AstNode):
    _rules = [("insert_statement", "_from_single_table")]
    _fields_spec = ["table", "columns", "values", "query"]

    @classmethod
    def _from_single_table(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)
        ctx = ctx.single_table_insert()

        insert_into_ctx = ctx.insert_into_clause()
        obj.table = visitor.visit(insert_into_ctx.general_table_ref())

        columns_ctx = insert_into_ctx.column_name_list()
        if columns_ctx:
            obj.columns = visitor.visit(columns_ctx)

        values_ctx = ctx.values_clause()
        if values_ctx:
            values_list_ctx = values_ctx.expression_list()
            obj = visitor.visit(values_list_ctx)

        query_ctx = ctx.select_statement()
        if query_ctx:
            obj.query = visitor.visit(query_ctx)

        return obj


class UpdateStmt(AstNode):
    _rules = [("update_statement", "_from_update")]
    _fields_spec = [
        "general_table_ref->table",
        "where_clause",
        "from_clause",
        "updates",
    ]

    @classmethod
    def _from_update(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)

        update_set_ctx = ctx.update_set_clause()
        if update_set_ctx.column_based_update_set_clause():
            obj.updates = visitor.visitChildren(
                update_set_ctx, predicate=is_terminal, simplify=False
            )

        return obj


class Update(AstNode):
    # TODO: BinExpr? Not fit for multiple columns combined?
    _rules = ["column_based_update_set_clause"]
    _fields_spec = ["column_name->column", "expression"]


class DeleteStmt(AstNode):
    _rules = ["delete_statement"]
    _fields_spec = ["general_table_ref->table", "where_clause"]


# class FunctionArgument


class Terminal(AstNode):
    _fields_spec = ["value"]
    DEBUG_INSTANCES = []

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls, *args, **kwargs)
        if DEBUG:
            cls.DEBUG_INSTANCES.append(instance)
            return instance
        else:
            return kwargs.get("value", "")

    def __str__(self):
        return self.value


# PARSE TREE VISITOR ----------------------------------------------------------


class AstVisitor(grammar.Visitor):
    def visitChildren(self, node, predicate=None, simplify=True):
        """This is the default visiting behaviour

        :param node: current node
        :param predicate: skip a child if this evaluates to false
        :param simplify: whether the result of the visited children should be combined if possible
        :return:
        """
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

        return self.result_to_ast(node, result, simplify=simplify)

    @staticmethod
    def result_to_ast(node, result, simplify=True):
        if len(result) == 0:
            return None
        elif simplify and len(result) == 1:
            return result[0]
        elif all(isinstance(res, Terminal) for res in result) or all(
            isinstance(res, str) for res in result
        ):
            if simplify:
                # TODO: log when this is used?
                # TODO: better combining of ctx?
                try:
                    ctx = copy.copy(result[0]._ctx)
                    ctx.symbol = copy.copy(ctx.symbol)
                    ctx.symbol.stop = result[-1]._ctx.symbol.stop
                except AttributeError:
                    ctx = node
                return Terminal(
                    ctx, value=" ".join(map(lambda t: getattr(t, "value", t), result))
                )
            else:
                return result
        elif all(
            isinstance(res, AstNode) and not isinstance(res, Unshaped) for res in result
        ) or (not simplify and all(res is not None for res in result)):
            return result
        else:
            if all(res is None for res in result):
                # return unparsed text
                result = node.start.getInputStream().getText(
                    node.start.start, node.stop.stop
                )
            return Unshaped(node, result)

    def defaultResult(self):
        return list()

    def aggregateResult(self, aggregate, nextResult):
        aggregate.append(nextResult)
        return aggregate

    def visitTerminal(self, ctx):
        """Converts case insensitive keywords and identifiers to lowercase"""
        text = ctx.getText()
        quotes = ["'", '"']
        if not (text[0] in quotes and text[-1] in quotes):
            text = text.lower()
        return Terminal(ctx, value=text)

    def visitErrorNode(self, node):
        return None

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

    def visitConstraint_clauses(self, ctx):
        if ctx.ADD():
            return AddConstraints._from_fields(self, ctx)
        if ctx.drop_constraint_clause():
            return DropConstraints._from_drop(self, ctx)

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
        "paren_column_list",
        "column_list",
        "relational_table",
        # "relational_properties",
        "column_name_list",
        "update_set_clause",
    ]


# TODO: convert more visitors now visitor generation is fixed
# for some reason can't get this to work as in tsql
# Override visit methods in AstVisitor for all nodes (in _rules) that convert to the AstNode classes
import inspect

for item in list(globals().values()):
    if inspect.isclass(item) and issubclass(item, AstNode):
        if getattr(item, "_rules", None) is not None:
            item._bind_to_visitor(AstVisitor)


def is_terminal(node):
    """Predicate to detect terminal nodes

    Consider adding a node to the visitor _remove_terminal list.
    """
    return not isinstance(node, Tree.TerminalNode)


# Override node visiting methods to add terminal child skipping in AstVisitor
for rule in AstVisitor._remove_terminal:
    # f = partial(AstVisitor.visitChildren, predicate = lambda n: not isinstance(n, Tree.TerminalNode))
    def skip_terminal_child_nodes(self, ctx):
        return self.visitChildren(ctx, predicate=is_terminal)

    bind_to_visitor(AstVisitor, rule, skip_terminal_child_nodes)


import pkg_resources

speaker_cfg = yaml.load(pkg_resources.resource_stream("antlr_plsql", "speaker.yml"))
speaker = Speaker(**speaker_cfg)

if __name__ == "__main__":
    query = """
SELECT id FROM artists WHERE id > 100
    """
    parse(query)
