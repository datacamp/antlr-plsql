import yaml
import pkg_resources

from antlr_ast.ast import (
    parse as parse_ast,
    Speaker,
    BaseAstVisitor,
    AliasVisitor,
    AliasNode,
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
    field_tree = BaseAstVisitor().visit(tree)
    alias_tree = AliasVisitor(Transformer()).visit(field_tree)

    return alias_tree


# AliasNodes


class Script(AliasNode):
    _fields_spec = ["body"]
    _rules = [("Sql_script", "_from_sql_script")]
    _priority = 0

    @classmethod
    def _from_sql_script(cls, node):
        obj = cls.from_spec(node)
        obj.body = cls.combine(
            node.unit_statement, node.sql_plus_command
        )  # todo: how does unit_statement get dml prop: transformer sets it (content of list fields is replaced)
        return obj


class SelectStmt(AliasNode):
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
        ("Query_block", "_from_query_block"),
        ("Select_statement", "_from_select"),
    ]

    _priority = 1

    @classmethod
    def _from_query_block(cls, node):
        # allowing arbitrary order for some clauses makes their results a single item list
        # future todo: represent unpacking with *
        # could also do testing to make sure clauses weren't specified multiple times
        query = cls.from_spec(node)
        unlist_clauses = cls._fields[cls._fields.index("group_by_clause") :]
        for k in unlist_clauses:
            attr = getattr(query, k, [])
            if isinstance(attr, list):
                setattr(query, k, attr[0] if len(attr) else None)

        return query

    @classmethod
    def _from_select(cls, node):
        select = node.subquery

        # todo: rule alias (type) check helper (check isinstance BaseClass + name of subtype)
        while type(select).__name__ == "SubqueryParen":
            # unpack brackets recursively
            select = select.subquery

        # strict: use safe access because only one rule alias has this property
        if select.query_block:
            select = select.query_block

        with_clause = node.subquery_factoring_clause
        if with_clause:
            select.with_clause = with_clause

        if not type(select).__name__ == "SubqueryCompound":
            select = cls.from_spec(select)

        return select


class Union(AliasNode):
    _fields_spec = ["left", "op", "right", "order_by_clause", "with_clause"]
    _rules = [("SubqueryCompound", "_from_subquery_compound")]

    @classmethod
    def _from_subquery_compound(cls, node):
        # hoists up ORDER BY clauses from the right SELECT statement
        # since the final ORDER BY applies to the entire statement (not just subquery)
        union = cls.from_spec(node)

        order_by = getattr(union.right, "order_by_clause", None)
        union.order_by_clause = order_by
        # remove from right SELECT
        if order_by:
            union.right.order_by_clause = None

        return union


class Identifier(AliasNode):
    _fields_spec = ["fields"]
    _rules = ["Dot_id"]


# TODO: similar nodes for keyword( combination)s?
class Star(AliasNode):
    _fields_spec = []
    _rules = ["Star"]


class TableAliasExpr(AliasNode):
    # TODO order_by_clause
    _fields_spec = ["alias=query_name", "alias_columns=paren_column_list", "subquery"]
    _rules = ["Factoring_element"]


class AliasExpr(AliasNode):
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
    def _unpack_alias(cls, node):
        obj = cls.from_spec(node)
        if obj.alias is not None:
            return obj
        else:
            return obj.expr


class BinaryExpr(AliasNode):
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
    def _from_mod(cls, node):
        bin_expr = cls.from_spec(node)
        ctx_not = node.NOT
        if ctx_not:
            return UnaryExpr(node, {"op": ctx_not, "expr": bin_expr})

        return bin_expr

    @classmethod
    def _from_in_expr(cls, node):
        # NOT IN produces unary expression
        bin_or_unary = cls._from_mod(node)
        right = node.subquery or node.expression_list
        if isinstance(bin_or_unary, UnaryExpr):
            bin_or_unary.expr.right = right
        else:
            bin_or_unary.right = right
        return bin_or_unary


class UnaryExpr(AliasNode):
    _fields_spec = ["op", "expr=unary_expression"]
    _rules = ["UnaryExpr", "CursorExpr", "NotExpr"]


class OrderByExpr(AliasNode):
    _fields_spec = ["expr=order_by_elements"]
    _rules = ["Order_by_clause"]


class SortBy(AliasNode):
    _fields_spec = ["expr=expression", "direction", "nulls"]
    _rules = ["Order_by_elements"]


class JoinExpr(AliasNode):
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


class Call(AliasNode):
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
        ("Aggregate_windowed_function", "_from_aggregate_call"),
        "ExtractCall",
        "FuncCall",
        ("WithinOrOverCall", "_from_within"),
        ("String_function", "_from_str_func"),
    ]

    @classmethod
    def _from_aggregate_call(cls, node):
        obj = cls.from_spec(node)
        # TODO: get_text (terminal not only in debug?)
        name = node.children[0]
        # TODO: (case) needed?
        if not isinstance(name, str):
            name = name._ctx.getText().lower()
        obj.name = name

        if obj.args is None:
            obj.args = []
        elif not isinstance(obj.args, Sequence):
            obj.args = [obj.args]
        return obj

    @classmethod
    def _from_within(cls, node):
        obj = cls.from_spec(node)

        within_or_over_part_ctx = node.within_or_over_part
        if within_or_over_part_ctx is not None:
            # works only for one such clause
            # TODO: convention for fields where multiple possible
            # >1 (>0): always, mostly, sometimes, exceptionally?
            for el in within_or_over_part_ctx:
                within_clause_ctx = el.order_by_clause
                if within_clause_ctx is not None:
                    obj.within_clause = within_clause_ctx
                over_clause_ctx = el.over_clause
                if over_clause_ctx is not None:
                    obj.over_clause = over_clause_ctx

        return obj

    @classmethod
    def _from_str_func(cls, node):
        obj = cls.from_spec(node)
        # todo: is field list if it is list in one (other) alternative?
        obj.args = cls.combine(
            node.expression,
            node.atom,
            node.expressions,
            node.quoted_string,
            node.table_element,
            node.standard_function,
        )
        return obj


class Cast(AliasNode):
    _fields_spec = [
        "type=type_spec",
        "statement=subquery",
        "statement=concatenation",
        "statement=expression",
        "statement=atom",
    ]
    _rules = ["CastCall"]


class OverClause(AliasNode):
    _fields_spec = [
        "partition=query_partition_clause",
        "order_by_clause",
        "windowing_clause",
    ]
    _rules = ["Over_clause"]


class Case(AliasNode):
    _fields_spec = [
        "switches=simple_case_when_part",
        "switches=searched_case_when_part",
        "else_expr=case_else_part",
    ]
    _rules = ["Simple_case_statement", "Searched_case_statement"]  # case_statement
    # 'label' in grammar not correct?


class CaseWhen(AliasNode):
    _fields_spec = ["when=whenExpr", "then=thenExpr"]
    _rules = ["Simple_case_when_part", "Searched_case_when_part"]


class PartitionBy(AliasNode):
    _fields_spec = ["expression"]
    _rules = ["Query_partition_clause"]


class RenameColumn(AliasNode):
    _fields_spec = ["old_name=old_column_name", "new_name=new_column_name"]
    _rules = ["Rename_column_clause"]


class Column(AliasNode):
    _fields_spec = [
        "name=column_name",
        "data_type=datatype",
        "data_type=type_name",
        "constraints=inline_constraint",
    ]
    _rules = ["Column_definition"]


class AddColumns(AliasNode):
    _fields_spec = ["columns=column_definition"]
    _rules = ["Add_column_clause"]


class DropColumn(AliasNode):
    _fields_spec = ["names"]
    _rules = ["Drop_column_clause"]


class AlterColumn(AliasNode):
    _fields_spec = ["name=column_name", "op", "data_type=datatype", "expression"]
    _rules = ["Alter_column_clause"]


class Reference(AliasNode):
    _fields_spec = ["table=tableview_name", "columns=paren_column_list"]
    _rules = ["References_clause"]


class CreateTable(AliasNode):
    _fields_spec = [
        "name=tableview_name",
        "temporary=TEMPORARY",
        "query=select_statement",
        # todo: + syntax (also multiple fields, e.g. constraints)
        "columns=relational_table.relational_properties.column_definition",
    ]
    _rules = ["Create_table"]


class AlterTable(AliasNode):
    _fields_spec = [
        "name=tableview_name",
        "changes=column_clauses",
        "changes=constraint_clauses",
    ]
    _rules = ["Alter_table"]


class AddConstraints(AliasNode):
    _fields_spec = ["constraints=out_of_line_constraint"]


class DropConstraints(AliasNode):
    # TODO: check exercises
    _fields_spec = ["constraints=drop_constraint_clause"]


class DropConstraint(AliasNode):
    _fields_spec = ["name=drop_primary_key_or_unique_or_generic_clause"]
    _rules = ["Drop_constraint_clause"]


class DropTable(AliasNode):
    _fields_spec = ["name=tableview_name", "existence_check"]
    _rules = [("Drop_table", "_from_table")]

    @classmethod
    def _from_table(cls, node):
        obj = cls.from_spec(node)

        # TODO: format? make combined rule and set using _field_spec?
        if node.IF and node.EXISTS:
            obj.existence_check = "if_exists"
        return obj


class Constraint(AliasNode):
    _fields_spec = [
        "name=constraint_name",
        "type",
        "columns=paren_column_list",
        "columns=foreign_key_clause.paren_column_list",
        "reference=foreign_key_clause.references_clause",
    ]
    _rules = [("Out_of_line_constraint", "_from_constraint")]

    @classmethod
    def _from_constraint(cls, node):
        obj = cls.from_spec(node)

        foreign_key_ctx = node.foreign_key_clause
        if node.UNIQUE:
            obj.type = "unique"
        elif node.PRIMARY and node.KEY:
            # TODO: format? make combined primary_key rule and set using _field_spec?
            obj.type = "primary_key"
        elif foreign_key_ctx and foreign_key_ctx.FOREIGN and foreign_key_ctx.KEY:
            obj.type = "foreign_key"
        elif node.CHECK:
            obj.type = "check"
        return obj


class InsertStmt(AliasNode):
    # TODO: use path field spec in more places
    _fields_spec = [
        "table=single_table_insert.insert_into_clause.general_table_ref",
        "columns=single_table_insert.insert_into_clause.paren_column_list",
        "values=single_table_insert.values_clause.expression_list",
        "query=single_table_insert.select_statement",
    ]
    _rules = ["Insert_statement"]


class UpdateStmt(AliasNode):
    _fields_spec = [
        "table=general_table_ref",
        "where_clause",
        "from_clause",
        "updates=update_set_clause.column_based_update_set_clause",
    ]
    _rules = ["Update_statement"]


class Update(AliasNode):
    # TODO: BinExpr? Not fit for multiple columns combined?
    _fields_spec = ["column=column_name", "expression"]
    _rules = ["Column_based_update_set_clause"]


class DeleteStmt(AliasNode):
    _fields_spec = ["table=general_table_ref", "where_clause"]
    _rules = ["Delete_statement"]


# class FunctionArgument


# PARSE TREE VISITOR ----------------------------------------------------------


# todo: remove
class Transformer:
    def visit_Relational_operator(self, node):
        # TODO: cleaner
        return Terminal(
            [node.get_text()], {"value": 0}, {}, node._ctx
        )  # node.children[0]?

    def visit_SubqueryParen(self, node):
        # todo: auto-simplify?
        return node.subquery

    def visit_StarTable(self, node):
        identifier = node.dot_id
        identifier.fields += [node.star]  # todo
        return identifier

    # function calls -------

    def visit_Function_argument_analytic(self, node):
        # future todo: declarative? needed?
        if not (node.respect_or_ignore_nulls or node.keep_clause):
            return node.argument
        else:
            return node

    # def visitIs_part(self, ctx):
    #    return ctx

    def visit_Constraint_clauses(self, node):
        # future todo: declarative?
        # - create grammar rule for each branch
        # - predicate in _rules
        if node.ADD:
            return AddConstraints.from_spec(node)
        if node.drop_constraint_clause:
            return DropConstraints.from_spec(node)

    # simple dropping of tokens -----------------------------------------------
    # Note can't filter out TerminalNodeImpl from some currently as in something like
    # "SELECT a FROM b WHERE 1", the 1 will be a terminal node in where_clause

    def visit_Where_clause(self, node):
        return node.current_of_clause or node.expression

    def visit_Limit_clause(self, node):
        return node.expression

    def visit_Column_alias(self, node):
        return node.r_id or node.alias_quoted_string

    def visit_Having_clause(self, node):
        return node.condition

    # visit single field
    # future todo: list of nodes that detect and parse all fields
    # alternative: visit_fields with manual list

    def visit_Expression_list(self, node):
        return node.expression

    def visit_Into_clause(self, node):
        return node.variable_name

    def visit_Drop_primary_key_or_unique_or_generic_clause(self, node):
        return node.constraint_name


# Override visit methods in AstVisitor for all nodes (in _rules) that convert to the AstNode classes
import inspect

for item in list(globals().values()):
    if inspect.isclass(item) and issubclass(item, AliasNode):
        if getattr(item, "_rules", None) is not None:
            item.bind_to_transformer(Transformer)


# Create Speaker

speaker_cfg = yaml.load(pkg_resources.resource_stream("antlr_plsql", "speaker.yml"))
speaker = Speaker(**speaker_cfg)

if __name__ == "__main__":
    query = """
SELECT id FROM artists WHERE id IN (SELECT * FROM abc)
    """
    parse(query)
