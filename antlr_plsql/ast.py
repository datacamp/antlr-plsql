import yaml
import pkg_resources

from antlr4.tree import Tree

from antlr_ast.ast import (
    parse as parse_ast,
    bind_to_visitor,
    AstNode,
    Speaker,
    BaseAstVisitor,
    # references for export:
    Terminal,
    AntlrException as ParseError,
)

from . import grammar

# AST -------------------------------------------------------------------------
# TODO: Finish Unary+Binary Expr
#       sql_script


def parse(sql_text, start="sql_script", **kwargs):
    tree = parse_ast(grammar, sql_text, start, **kwargs)
    return AstVisitor().visit(tree)


# AstNodes


class Script(AstNode):
    _fields_spec = ["body"]
    _rules = [("sql_script", "_from_sql_script")]
    _priority = 0

    @classmethod
    def _from_sql_script(cls, visitor, ctx):
        # future todo: extract body rule in grammar to use _fields_spec for this?
        # future todo: support + syntax between multiple fields to combine
        # + op semantics:  AND for terminals, else flat list concat for list
        body = visitor.visitChildren(ctx, predicate=is_terminal, simplify=False)
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
        # allowing arbitrary order for some clauses makes their results a single item list
        # future todo: represent unpacking with *
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


# TODO: similar nodes for keyword( combination)s?
class Star(AstNode):
    _fields_spec = []
    _rules = ["star"]


class TableAliasExpr(AstNode):
    # TODO order_by_clause
    _fields_spec = ["alias=query_name", "alias_columns=paren_column_list", "subquery"]
    _rules = ["factoring_element"]


class AliasExpr(AstNode):
    _fields_spec = [
        # Alias_expr
        "alias",
        "expr",
        # TableRefAux
        "expr=table_ref_aux.dml_table_expression_clause",
        "alias=table_alias",
    ]
    _rules = [("Alias_expr", "_unpack_alias"), ("TableRefAux", "_unpack_alias")]

    @classmethod
    def _unpack_alias(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)
        if obj.alias is not None:
            return obj
        else:
            return obj.expr


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
    _fields_spec = ["op", "expr=unary_expression"]
    _rules = ["UnaryExpr", "CursorExpr", "NotExpr"]


class OrderByExpr(AstNode):
    _fields_spec = ["expr=order_by_elements"]
    _rules = ["order_by_clause"]


class SortBy(AstNode):
    _fields_spec = ["expr=expression", "direction", "nulls"]
    _rules = ["order_by_elements"]


class JoinExpr(AstNode):
    _fields_spec = [
        "left=table_ref",
        "join_type=join_clause.join_type",
        "right=join_clause.table_ref",
        "cond=join_clause.join_on_part",
        # fields below are Oracle specific
        "using=join_clause.join_using_part",
        "query_partition_clause=join_clause.query_partition_clause",
    ]
    _rules = ["JoinExpr"]


from collections.abc import Sequence


class Call(AstNode):
    _fields_spec = [
        "name",
        "name=dot_id",
        "pref",
        "args",
        "args=function_argument",
        "args=function_argument_analytic",
        "component=regular_id",
        "expr=concatenation",
        "within_clause",
        "over_clause",
    ]
    _rules = [
        ("aggregate_windowed_function", "_from_aggregate_call"),
        "ExtractCall",
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
        obj.args = visitor.visitChildren(ctx, predicate=is_terminal, simplify=False)
        return obj


class Cast(AstNode):
    _fields_spec = [
        "type=type_spec",
        "statement=subquery",
        "statement=concatenation",
        "statement=expression",
        "statement=atom",
    ]
    _rules = ["CastCall"]


class OverClause(AstNode):
    _rules = ["over_clause"]
    _fields_spec = [
        "partition=query_partition_clause",
        "order_by_clause",
        "windowing_clause",
    ]


class Case(AstNode):
    _rules = ["simple_case_statement", "searched_case_statement"]  # case_statement
    _fields_spec = [
        "switches=simple_case_when_part",
        "switches=searched_case_when_part",
        "else_expr=case_else_part",
    ]
    # 'label' in grammar not correct?


class CaseWhen(AstNode):
    _rules = ["simple_case_when_part", "searched_case_when_part"]
    _fields_spec = ["when=whenExpr", "then=thenExpr"]


class PartitionBy(AstNode):
    _fields_spec = ["expression"]
    _rules = ["query_partition_clause"]


class RenameColumn(AstNode):
    _fields_spec = ["old_name=old_column_name", "new_name=new_column_name"]
    _rules = ["rename_column_clause"]


class Column(AstNode):
    _fields_spec = [
        "name=column_name",
        "data_type=datatype",
        "data_type=type_name",
        "constraints=inline_constraint",
    ]
    _rules = ["column_definition"]


class AddColumns(AstNode):
    _fields_spec = ["columns=column_definition"]
    _rules = ["add_column_clause"]


class DropColumn(AstNode):
    _fields_spec = ["names"]
    _rules = ["drop_column_clause"]


class AlterColumn(AstNode):
    _fields_spec = ["name=column_name", "op", "data_type=datatype", "expression"]
    _rules = ["alter_column_clause"]


class Reference(AstNode):
    _fields_spec = ["table=tableview_name", "columns=paren_column_list"]
    _rules = ["references_clause"]


class CreateTable(AstNode):
    _fields_spec = [
        "name=tableview_name",
        "temporary=TEMPORARY",
        "query=select_statement",
        # todo: + syntax (also multiple fields, e.g. constraints)
        "columns=relational_table.relational_properties.column_definition",
    ]
    _rules = ["create_table"]


class AlterTable(AstNode):
    _fields_spec = [
        "name=tableview_name",
        "changes=column_clauses",
        "changes=constraint_clauses",
    ]
    _rules = ["alter_table"]


class AddConstraints(AstNode):
    _fields_spec = ["constraints=out_of_line_constraint"]


class DropConstraints(AstNode):
    # TODO: check exercises
    _fields_spec = ["constraints=drop_constraint_clause"]


class DropConstraint(AstNode):
    _fields_spec = ["name=drop_primary_key_or_unique_or_generic_clause"]
    _rules = ["drop_constraint_clause"]


class DropTable(AstNode):
    _fields_spec = ["name=tableview_name", "existence_check"]
    _rules = [("drop_table", "_from_table")]

    @classmethod
    def _from_table(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)

        # TODO: format? make combined rule and set using _field_spec?
        if ctx.IF() and ctx.EXISTS():
            obj.existence_check = "if_exists"
        return obj


class Constraint(AstNode):
    _fields_spec = [
        "name=constraint_name",
        "type",
        "columns=foreign_key_clause.paren_column_list",
        "reference=foreign_key_clause.references_clause",
    ]
    _rules = [("out_of_line_constraint", "_from_constraint")]

    @classmethod
    def _from_constraint(cls, visitor, ctx):
        obj = cls._from_fields(visitor, ctx)

        foreign_key_ctx = ctx.foreign_key_clause()
        if ctx.UNIQUE():
            obj.type = "unique"
        elif ctx.PRIMARY() and ctx.KEY():
            # TODO: format? make combined primary_key rule and set using _field_spec?
            obj.type = "primary_key"
        elif foreign_key_ctx and foreign_key_ctx.FOREIGN() and foreign_key_ctx.KEY():
            obj.type = "foreign_key"
        elif ctx.CHECK():
            obj.type = "check"
        return obj


class InsertStmt(AstNode):
    # TODO: use path field spec in more places
    _fields_spec = [
        "table=single_table_insert.insert_into_clause.general_table_ref",
        "columns=single_table_insert.insert_into_clause.paren_column_list",
        "values=single_table_insert.values_clause.expression_list",
        "query=single_table_insert.select_statement",
    ]
    _rules = ["insert_statement"]


class UpdateStmt(AstNode):
    _fields_spec = [
        "table=general_table_ref",
        "where_clause",
        "from_clause",
        "updates=update_set_clause.column_based_update_set_clause",
    ]
    _rules = ["update_statement"]


class Update(AstNode):
    # TODO: BinExpr? Not fit for multiple columns combined?
    _fields_spec = ["column=column_name", "expression"]
    _rules = ["column_based_update_set_clause"]


class DeleteStmt(AstNode):
    _fields_spec = ["table=general_table_ref", "where_clause"]
    _rules = ["delete_statement"]


# class FunctionArgument


# PARSE TREE VISITOR ----------------------------------------------------------


class AstVisitor(BaseAstVisitor, grammar.Visitor):
    def visitSubqueryParen(self, ctx):
        return self.visit(ctx.subquery())

    def visitStarTable(self, ctx):
        identifier = self.visit(ctx.dot_id())
        identifier.fields += [self.visit(ctx.star())]
        return identifier

    # function calls -------

    def visitFunction_argument_analytic(self, ctx):
        # future todo: declarative?
        if not (ctx.respect_or_ignore_nulls() or ctx.keep_clause()):
            return [self.visit(arg) for arg in ctx.argument()]
        else:
            return self.visitChildren(ctx)

    # def visitIs_part(self, ctx):
    #    return ctx

    def visitConstraint_clauses(self, ctx):
        # future todo: declarative?
        # - create grammar rule for each branch
        # - predicate in _rules
        if ctx.ADD():
            return AddConstraints._from_fields(self, ctx)
        if ctx.drop_constraint_clause():
            return DropConstraints._from_fields(self, ctx)

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

    # visit single field
    # future todo: list of nodes that detect and parse all fields
    # alternative: visit_fields with manual list

    def visitExpression_list(self, ctx):
        # these patterns are equivalent:
        return self.visit_field(ctx, ctx.expression)
        # return [self.visit(expr) for expr in ctx.expression()]
        # return self.visitChildren(ctx, predicate = lambda n: not isinstance(n, Tree.TerminalNode))

    def visitInto_clause(self, ctx):
        return self.visit_field(ctx, ctx.variable_name)

    def visitDrop_primary_key_or_unique_or_generic_clause(self, ctx):
        return self.visit_field(ctx, ctx.constraint_name)

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
        "update_set_clause",
    ]


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


# Create Speaker

speaker_cfg = yaml.load(pkg_resources.resource_stream("antlr_plsql", "speaker.yml"))
speaker = Speaker(**speaker_cfg)

if __name__ == "__main__":
    query = """
SELECT id FROM artists WHERE id > 100
    """
    parse(query)
