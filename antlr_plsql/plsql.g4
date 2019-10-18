/**
 * Oracle(c) PL/SQL 11g Parser
 *
 * Copyright (c) 2009-2011 Alexandre Porcelli <alexandre.porcelli@gmail.com>
 * Copyright (c) 2015 Ivan Kochurkin (KvanTTT, kvanttt@gmail.com).
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
grammar plsql;

// TODO: order rules: create, alter, drop table rules
// keyword shortcuts: e.g. TEMP[ORARY]
// regular_id keywords update? (sync with lexer keywords) (keywords can be identifiers)
// integrate literal / string_function in expression (in unary_expression (~ standard function)? in atom (~ constant)?)

swallow_to_semi
    : ~';'+
    ;

compilation_unit
    : unit_statement* EOF
    ;

sql_script
    : ((unit_statement | sql_plus_command) (SEMICOLON (unit_statement | sql_plus_command ))* SEMICOLON?)? EOF
    ;

// https://www.postgresql.org/docs/9.4/sql-explain.html
sql_explain
    : EXPLAIN (ANALYZE)? (VERBOSE)?
    ;

unit_statement
    : (sql_explain)? unit_statement_body
    ;

unit_statement_body
    : alter_function
    | alter_package
    | alter_procedure
    | alter_sequence
    | alter_trigger
    | alter_type
    | alter_table
    | alter_permission

    | create_function_body
    | create_procedure_body
    | create_package

    | create_index
    | create_table
    | create_view
//  | create_directory //TODO
    | create_materialized_view
    | refresh_materialized_view

    | create_sequence
    | create_trigger
    | create_type
    | create_role

    | drop_function
    | drop_package
    | drop_procedure
    | drop_sequence
    | drop_trigger
    | drop_type
    | data_manipulation_language_statements
    | drop_table
    ;

create_role
    : CREATE ROLE role_name (WITH? role_option+)?
    ;

role_option
    : LOGIN
    | CREATEDB
    | CREATEROLE
    ;

refresh_materialized_view
    : REFRESH MATERIALIZED VIEW tableview_name
    ;


create_materialized_view
    : CREATE MATERIALIZED VIEW tableview_name
      (OF type_name )?
//scoped_table_ref and column alias goes here  TODO
        ( ON PREBUILT TABLE ( (WITH | WITHOUT) REDUCED PRECISION)?
        | physical_properties?  (CACHE | NOCACHE)? parallel_clause? build_clause?
        )
        ( USING INDEX ( (physical_attributes_clause | TABLESPACE mv_tablespace=id_expression)+ )*
        | USING NO INDEX
        )?
        create_mv_refresh?
        (FOR UPDATE)?
        ( (DISABLE | ENABLE) QUERY REWRITE )?
        AS subquery
    ;

create_mv_refresh
    : ( NEVER REFRESH
      | REFRESH
         ( (FAST | COMPLETE | FORCE)
         | ON (DEMAND | COMMIT)
         | (START WITH | NEXT) //date goes here TODO
         | WITH (PRIMARY KEY | ROWID)
         | USING
             ( DEFAULT (MASTER | LOCAL)? ROLLBACK SEGMENT
             | (MASTER | LOCAL)? ROLLBACK SEGMENT rb_segment=REGULAR_ID
             )
         | USING (ENFORCED | TRUSTED) CONSTRAINTS
         )+
      )
    ;

build_clause
    : BUILD (IMMEDIATE | DEFERRED)
    ;

alter_permission //https://www.postgresql.org/docs/9.5/sql-revoke.html
    : REVOKE permission_options ON TABLE? tableview_name FROM GROUP? (PUBLIC | role_name)
    | GRANT permission_options ON TABLE? tableview_name TO GROUP? (PUBLIC | role_name)
    | GRANT role_name (',' role_name)* TO role_name (',' role_name)*
    | REVOKE role_name (',' role_name)* FROM role_name (',' role_name)*
    ;

permission_options
    : (','? (SELECT | INSERT | UPDATE | DELETE | TRUNCATE | REFERENCES | TRIGGER))+
    ;

create_view
    : CREATE (OR REPLACE)? (OR? FORCE)? EDITIONING? VIEW
      tableview_name view_options?
      AS subquery subquery_restriction_clause?
    ;

view_options
    :  view_alias_constraint
//  | object_view_clause  // Available at https://github.com/antlr/grammars-v4/blob/master/plsql/PlSqlParser.g4
//  | xmltype_view_clause //TODO
    ;

view_alias_constraint
    : '(' ( ','? (table_alias inline_constraint* | out_of_line_constraint) )+ ')'
    ;

create_index
    : CREATE (UNIQUE | BITMAP)? INDEX index_name
       ON (cluster_index_clause | table_index_clause | bitmap_join_index_clause)
       UNUSABLE?
    ;

cluster_index_clause
    : CLUSTER cluster_name index_attributes?
    ;

cluster_name
    : (id_expression '.')? id_expression
    ;

index_attributes
    : ( physical_attributes_clause
      | logging_clause
      | TABLESPACE (tablespace | DEFAULT)
      | key_compression
      | sort_or_nosort
      | REVERSE
      | visible_or_invisible
      | parallel_clause
      )+
    ;

tablespace
    : regular_id
    ;

key_compression
    : NOCOMPRESS
    | COMPRESS UNSIGNED_INTEGER
    ;

sort_or_nosort
    : SORT
    | NOSORT
    ;

visible_or_invisible
    : VISIBLE
    | INVISIBLE
    ;

parallel_clause
    : NOPARALLEL
    | PARALLEL parallel_count=UNSIGNED_INTEGER?
    ;

table_index_clause
    : tableview_name table_alias? '(' (','? index_expr (ASC | DESC)? )+ ')'
          index_properties?
    ;

index_expr
    : column_name
    | expression
    ;

index_properties
    : (global_partitioned_index | local_partitioned_index | index_attributes)+
    | INDEXTYPE IS (domain_index_clause | xmlindex_clause)
    ;

global_partitioned_index
    : GLOBAL PARTITION BY (RANGE paren_column_list '(' index_partitioning_clause ')'
                          | HASH paren_column_list
                                            (individual_hash_partitions
                                            | hash_partitions_by_quantity
                                            )
                          )
    ;

index_partitioning_clause
    : PARTITION partition_name? VALUES LESS THAN '(' (','? literal)+ ')'
        segment_attributes_clause?
    ;

partition_name
    : regular_id
    ;

literal
    : CHAR_STRING
    | string_function
    | numeric
    | MAXVALUE
    ;

string_function
    : name=SUBSTRING '(' expression ',' expression (',' expression)? ')'  // todo: incorrect?
    | name=SUBSTRING '(' expression (FROM atom)? (FOR atom)? ')'
    | name=TO_CHAR '(' (table_element | standard_function | expression)
                  (',' quoted_string)? (',' quoted_string)? ')'
    | name=DECODE '(' expressions  ')'
    | name=CHR '(' concatenation USING NCHAR_CS ')'
    | name=NVL '(' expression ',' expression ')'
    | name=TRIM '(' ((LEADING | TRAILING | BOTH)? quoted_string? FROM)? concatenation ')'
    | name=TO_DATE '(' expression (',' quoted_string)? ')'
    | name=CONCAT '(' ( (quoted_string|expression) ',')+ (quoted_string|expression) ')'
    ;

expressions
    : expression (',' expression)*
    ;

individual_hash_partitions
    : '(' (','? PARTITION partition_name? partitioning_storage_clause?)+ ')'
    ;

partitioning_storage_clause
    : ( TABLESPACE tablespace
      | OVERFLOW (TABLESPACE tablespace)?
      | table_compression
      | key_compression
      | lob_partitioning_storage
      | VARRAY varray_item STORE AS (BASICFILE | SECUREFILE)? LOB lob_segname
      )+
    ;

table_compression
    : COMPRESS
        ( BASIC
        | FOR ( OLTP
              | (QUERY | ARCHIVE) (LOW | HIGH)?
              )
        )?
    | NOCOMPRESS
    ;

lob_partitioning_storage
    : LOB '(' lob_item ')'
       STORE AS (BASICFILE | SECUREFILE)?
               (lob_segname ('(' TABLESPACE tablespace ')' )?
               | '(' TABLESPACE tablespace ')'
               )
    ;

lob_item
    : regular_id
    ;

lob_segname
    : regular_id
    ;

varray_item
    : (id_expression '.')? (id_expression '.')? id_expression
    ;

hash_partitions_by_quantity
    : PARTITIONS hash_partition_quantity
       (STORE IN '(' (','? tablespace)+ ')')?
         (table_compression | key_compression)?
         (OVERFLOW STORE IN '(' (','? tablespace)+ ')' )?
    ;

hash_partition_quantity
    : UNSIGNED_INTEGER
    ;

local_partitioned_index
    : LOCAL (on_range_partitioned_table
            | on_list_partitioned_table
            | on_hash_partitioned_table
            | on_comp_partitioned_table
            )?
    ;

on_range_partitioned_table
    : '(' (','? PARTITION partition_name?
              ((segment_attributes_clause | key_compression)+ )?
              UNUSABLE? )+
      ')'
    ;

on_list_partitioned_table
    : '(' (','? PARTITION partition_name?
              ((segment_attributes_clause | key_compression)+ )?
              UNUSABLE? )+
      ')'
    ;

on_hash_partitioned_table
    : STORE IN '(' (','? tablespace)+ ')'
    | '(' (','? PARTITION partition_name? (TABLESPACE tablespace)?
                key_compression? UNUSABLE?)+
      ')'
    ;

on_comp_partitioned_table
    : (STORE IN '(' (','? tablespace)+ ')' )?
        '(' (','? PARTITION partition_name?
            ((segment_attributes_clause | key_compression)+)?
            UNUSABLE index_subpartition_clause? )+
        ')'
    ;

index_subpartition_clause
    : STORE IN '(' (','? tablespace)+ ')'
    | '(' (','? SUBPARTITION subpartition_name? (TABLESPACE tablespace)?
        key_compression? UNUSABLE?)+
      ')'
    ;

subpartition_name
    : partition_name
    ;

domain_index_clause
    : indextype local_domain_index_clause? parallel_clause? (PARAMETERS '(' odci_parameters ')' )?
    ;

indextype
    : (id_expression '.')? id_expression
    ;

odci_parameters
    : CHAR_STRING
    ;

local_domain_index_clause
    : LOCAL ('(' (','? PARTITION partition_name (PARAMETERS '(' odci_parameters ')' )? )+ ')' )?
    ;

xmlindex_clause
    : (XDB '.')? XMLINDEX local_xmlindex_clause?
        parallel_clause? //TODO xmlindex_parameters_clause?
    ;

local_xmlindex_clause
    : LOCAL ('(' (','? PARTITION partition_name //TODO xmlindex_parameters_clause?
                                                       )+ ')')?
    ;

bitmap_join_index_clause
    : tableview_name '(' (','? (tableview_name | table_alias)? column_name (ASC | DESC)? )+ ')'
        FROM (','? tableview_name table_alias)+
        where_clause local_partitioned_index? index_attributes?
    ;

create_table
    : CREATE (GLOBAL? TEMPORARY)? TABLE tableview_name
        (relational_table | object_table | xmltype_table) (AS select_statement)?
      (PARTITION OF tableview_name ((FOR VALUES IN '(' expression (',' expression)* ')')| DEFAULT) )?
    ;

relational_table
    : ('(' relational_properties ')')?
      (ON COMMIT (DELETE | PRESERVE) ROWS)?
      physical_properties? column_properties? table_partitioning_clauses?
      (CACHE | NOCACHE)? (RESULT_CACHE '(' MODE (DEFAULT | FORCE) ')')?
      parallel_clause?
      (ROWDEPENDENCIES | NOROWDEPENDENCIES)?
      (enable_disable_clause+)? row_movement_clause? flashback_archive_clause?
    ;

relational_properties
    : (','? (column_definition
            | virtual_column_definition
            | out_of_line_constraint
            | out_of_line_ref_constraint
            | supplemental_logging_props
            )
      )+
    ;

column_definition
    : column_name (datatype | type_name)
         SORT?  (DEFAULT expression)? (ENCRYPT (USING  CHAR_STRING)? (IDENTIFIED BY regular_id)? CHAR_STRING? (NO? SALT)? )?  (inline_constraint* | inline_ref_constraint) (DEFAULT expression)?
    ;

inline_ref_constraint
    : SCOPE IS tableview_name
    | WITH ROWID
    | (CONSTRAINT constraint_name)? references_clause constraint_state?
    ;

virtual_column_definition
    : column_name datatype? (GENERATED ALWAYS)? AS '(' expression ')'
        VIRTUAL? inline_constraint*
    ;

out_of_line_constraint
    : ( (CONSTRAINT constraint_name)?
          ( UNIQUE paren_column_list
          | PRIMARY KEY paren_column_list
          | foreign_key_clause
          | CHECK '(' expression ')'
          )
       )
      constraint_state?
    ;

foreign_key_clause
    : FOREIGN KEY paren_column_list references_clause on_delete_clause?
    ;

on_delete_clause
    : ON DELETE (CASCADE | SET NULL)
    ;

out_of_line_ref_constraint
    : SCOPE FOR '(' ref_col_or_attr=regular_id ')' IS tableview_name
    | REF '(' ref_col_or_attr=regular_id ')' WITH ROWID
    | (CONSTRAINT constraint_name)? FOREIGN KEY '(' ( ','? ref_col_or_attr=regular_id)+ ')' references_clause constraint_state?
    ;

supplemental_logging_props
    : SUPPLEMENTAL LOG (supplemental_log_grp_clause | supplemental_id_key_clause)
    ;

supplemental_log_grp_clause
    : GROUP log_grp '(' (','? regular_id (NO LOG)?)+ ')' ALWAYS?
    ;

log_grp
    : UNSIGNED_INTEGER
    ;

supplemental_id_key_clause
    : DATA '('( ','? ( ALL
                     | PRIMARY KEY
                     | UNIQUE
                     | FOREIGN KEY
                     )
              )+
           ')'
      COLUMNS
    ;

physical_properties
    : deferred_segment_creation?  segment_attributes_clause table_compression?
    ;

deferred_segment_creation
    : SEGMENT CREATION (IMMEDIATE | DEFERRED)
    ;

segment_attributes_clause
    : ( physical_attributes_clause
      | TABLESPACE tablespace_name=id_expression
      | logging_clause
      )+
    ;

physical_attributes_clause
    : (PCTFREE pctfree=UNSIGNED_INTEGER
      | PCTUSED pctused=UNSIGNED_INTEGER
      | INITRANS inittrans=UNSIGNED_INTEGER
      | storage_clause
      )+
    ;

storage_clause
    : STORAGE '('
         (INITIAL initial_size=size_clause
         | NEXT next_size=size_clause
         | MINEXTENTS minextents=(UNSIGNED_INTEGER | UNLIMITED)
         | MAXEXTENTS minextents=(UNSIGNED_INTEGER | UNLIMITED)
         | PCTINCREASE pctincrease=UNSIGNED_INTEGER
         | FREELISTS freelists=UNSIGNED_INTEGER
         | FREELIST GROUPS freelist_groups=UNSIGNED_INTEGER
         | OPTIMAL (size_clause | NULL )
         | BUFFER_POOL (KEEP | RECYCLE | DEFAULT)
         | FLASH_CACHE (KEEP | NONE | DEFAULT)
         | ENCRYPT
         )+
       ')'
    ;

//Technically, this should only allow 'K' | 'M' | 'G' | 'T' | 'P' | 'E'
// but having issues with examples/numbers01.sql line 11 "sysdate -1m"
size_clause
    : UNSIGNED_INTEGER REGULAR_ID?
    ;

logging_clause
    : LOGGING
    | NOLOGGING
    | FILESYSTEM_LIKE_LOGGING
    ;

column_properties
    : object_type_col_properties
    | nested_table_col_properties
    | (varray_col_properties | lob_storage_clause) //TODO '(' ( ','? lob_partition_storage)+ ')'
    | xmltype_column_properties
    ;

object_type_col_properties
    : COLUMN column=regular_id substitutable_column_clause
    ;

substitutable_column_clause
    : ELEMENT? IS OF TYPE? '(' type_name ')'
    | NOT? SUBSTITUTABLE AT ALL LEVELS
    ;

nested_table_col_properties
    : NESTED TABLE  (nested_item | COLUMN_VALUE) substitutable_column_clause? (LOCAL | GLOBAL)?
       STORE AS tableview_name ( '(' ( '(' object_properties ')'
                                     | physical_properties
                                     | column_properties
                                     )+
                                  ')'
                               )?
        (RETURN AS? (LOCATOR | VALUE) )?
     ;

nested_item
    : regular_id
    ;

object_properties
    : (column_name | attribute_name) (DEFAULT expression)? ((','? inline_constraint)+ | inline_ref_constraint)?
    | out_of_line_constraint
    | out_of_line_ref_constraint
    | supplemental_logging_props
    ;

inline_constraint
    : (CONSTRAINT constraint_name)?
        ( NOT? NULL
        | UNIQUE
        | PRIMARY KEY
        | references_clause
        | check_constraint
        )
      constraint_state?
    ;

references_clause
    : REFERENCES tableview_name paren_column_list
    ;

paren_column_list
    : '(' column_list ')'
    // todo: from column_name_list
    // : '(' column_name (',' column_name)* ')'
    ;

column_list
    : (','? column_name)+
    ;

check_constraint
    : CHECK '(' condition ')' DISABLE?
    ;

constraint_state
    : ( NOT? DEFERRABLE
      | INITIALLY (IMMEDIATE|DEFERRED)
      | (RELY|NORELY)
      | (ENABLE|DISABLE)
      | (VALIDATE|NOVALIDATE)
      | using_index_clause
      )+
    ;

using_index_clause
    : USING INDEX (index_name | '(' create_index ')' | index_attributes )?
    ;

varray_col_properties
    : VARRAY varray_item ( substitutable_column_clause? varray_storage_clause
                         | substitutable_column_clause
                         )
    ;

varray_storage_clause
    : STORE AS (SECUREFILE|BASICFILE)? LOB ( lob_segname? '(' lob_storage_parameters ')'
                                           | lob_segname
                                           )
    ;

lob_storage_parameters
    :  TABLESPACE tablespace | (lob_parameters storage_clause? )
    |  storage_clause
    ;

lob_parameters
    : ( (ENABLE | DISABLE) STORAGE IN ROW
      | CHUNK UNSIGNED_INTEGER
      | PCTVERSION UNSIGNED_INTEGER
      | FREEPOOLS UNSIGNED_INTEGER
      | lob_retention_clause
      | lob_deduplicate_clause
      | lob_compression_clause
      | ENCRYPT encryption_spec
      | DECRYPT
      | (CACHE | NOCACHE | CACHE READS) logging_clause?
      )+
    ;

lob_retention_clause
    : RETENTION (MAX | MIN UNSIGNED_INTEGER | AUTO | NONE)?
    ;

lob_deduplicate_clause
    : DEDUPLICATE
    | KEEP_DUPLICATES
    ;

lob_compression_clause
    : NOCOMPRESS
    | COMPRESS (HIGH | MEDIUM | LOW)?
    ;

encryption_spec
    : (USING  CHAR_STRING)? (IDENTIFIED BY REGULAR_ID)? CHAR_STRING? (NO? SALT)?
    ;

lob_storage_clause
    : LOB ( '(' (','? lob_item)+ ')' STORE AS ( (SECUREFILE|BASICFILE) | '(' lob_storage_parameters ')' )+
          | '(' lob_item ')' STORE AS ( (SECUREFILE | BASICFILE) | lob_segname | '(' lob_storage_parameters ')' )+
          )
    ;

xmltype_column_properties
    : XMLTYPE COLUMN? column_name xmltype_storage? xmlschema_spec?
    ;

xmltype_storage
    : STORE  AS (OBJECT RELATIONAL
                | (SECUREFILE | BASICFILE)? (CLOB | BINARY XML) (lob_segname ('(' lob_parameters ')')? | '(' lob_parameters ')')?
                )
    | STORE VARRAYS AS (LOBS | TABLES)
    ;

xmlschema_spec
    : (XMLSCHEMA DELIMITED_ID)? ELEMENT DELIMITED_ID
         (allow_or_disallow NONSCHEMA)?
         (allow_or_disallow ANYSCHEMA)?
    ;

allow_or_disallow
    : ALLOW
    | DISALLOW
    ;

table_partitioning_clauses
    : range_partitions
    | list_partitions
    | hash_partitions
    | composite_range_partitions
    | composite_list_partitions
    | composite_hash_partitions
    | reference_partitioning
    | system_partitioning
    ;

range_partitions
    : PARTITION BY RANGE paren_column_list
        (INTERVAL '(' expression ')' (STORE IN '(' (','? tablespace)+ ')' )? )?
          '(' (','? PARTITION partition_name? range_values_clause table_partition_description)+ ')'
    ;

range_values_clause
    : VALUES LESS THAN '(' (','? literal)+ ')'
    ;

table_partition_description
    : deferred_segment_creation? segment_attributes_clause?
        (table_compression | key_compression)?
        (OVERFLOW segment_attributes_clause? )?
        (lob_storage_clause | varray_col_properties | nested_table_col_properties)?
    ;

list_partitions
    : PARTITION BY LIST '(' column_name ')'
        ('(' (','? PARTITION partition_name? list_values_clause table_partition_description )+ ')')?
    ;

list_values_clause
    : VALUES '(' ((','? literal)+ | DEFAULT) ')'
    ;

hash_partitions
    : PARTITION BY HASH paren_column_list
        (individual_hash_partitions | hash_partitions_by_quantity)
    ;

composite_range_partitions
    : PARTITION BY RANGE paren_column_list
       (INTERVAL '(' expression ')' (STORE IN '(' (','? tablespace)+ ')' )? )?
       (subpartition_by_range | subpartition_by_list | subpartition_by_hash)
         '(' (','? range_partition_desc)+ ')'
    ;

subpartition_by_range
    : SUBPARTITION BY RANGE paren_column_list subpartition_template?
    ;

subpartition_by_list
    : SUBPARTITION BY LIST '(' column_name ')' subpartition_template?
    ;

subpartition_template
    : SUBPARTITION TEMPLATE
        ( ( '(' ( (','? range_subpartition_desc)+
                | (','? list_subpartition_desc)+
                | (','? individual_hash_subparts)+
                )
            ')'
          | hash_subpartition_quantity
          )
        )
    ;

range_subpartition_desc
    : SUBPARTITION subpartition_name? range_values_clause partitioning_storage_clause?
    ;

list_subpartition_desc
    : SUBPARTITION subpartition_name? list_values_clause partitioning_storage_clause?
    ;

individual_hash_subparts
    : SUBPARTITION subpartition_name? partitioning_storage_clause?
    ;

hash_subpartition_quantity
    : UNSIGNED_INTEGER
    ;

subpartition_by_hash
    : SUBPARTITION BY HASH paren_column_list
       (SUBPARTITIONS UNSIGNED_INTEGER (STORE IN '(' (','? tablespace)+ ')' )?
       | subpartition_template
       )?
    ;

range_partition_desc
    : PARTITION partition_name? range_values_clause table_partition_description
        ( ( '(' ( (','? range_subpartition_desc)+
                | (','? list_subpartition_desc)+
                | (','? individual_hash_subparts)+
                )
            ')'
          | hash_subparts_by_quantity
          )
        )?
    ;

hash_subparts_by_quantity
    : SUBPARTITIONS UNSIGNED_INTEGER (STORE IN '(' (','? tablespace)+ ')' )?
    ;

composite_list_partitions
    : PARTITION BY LIST '(' column_name ')'
       (subpartition_by_range | subpartition_by_list | subpartition_by_hash)
        '(' (','? list_partition_desc)+ ')'
    ;

list_partition_desc
    : PARTITION partition_name? list_values_clause table_partition_description
        ( ( '(' ( (','? range_subpartition_desc)+
                | (','? list_subpartition_desc)+
                | (','? individual_hash_subparts)+
                )
            ')'
          | hash_subparts_by_quantity
          )
        )?
    ;

composite_hash_partitions
    : PARTITION BY HASH '(' (',' column_name)+ ')'
       (subpartition_by_range | subpartition_by_list | subpartition_by_hash)
         (individual_hash_partitions | hash_partitions_by_quantity)
    ;

reference_partitioning
    : PARTITION BY REFERENCE '(' regular_id ')'
             ('(' (','? reference_partition_desc)+ ')')?
    ;

reference_partition_desc
    : PARTITION partition_name? table_partition_description
    ;

system_partitioning
    : PARTITION BY SYSTEM
       (PARTITIONS UNSIGNED_INTEGER | (','? reference_partition_desc)+)?
    ;

enable_disable_clause
    : (ENABLE | DISABLE) (VALIDATE | NOVALIDATE)?
         (UNIQUE paren_column_list
         | PRIMARY KEY
         | CONSTRAINT constraint_name
         ) using_index_clause? exceptions_clause?
         CASCADE? ((KEEP | DROP) INDEX)?
    ;

exceptions_clause
    : EXCEPTIONS INTO tableview_name
    ;

row_movement_clause
    : (ENABLE | DISABLE)? ROW MOVEMENT
    ;

flashback_archive_clause
    : FLASHBACK ARCHIVE flashback_archive=REGULAR_ID
    | NO FLASHBACK ARCHIVE
    ;

object_table
    : OF type_name object_table_substitution?
      ('(' (','? object_properties)+ ')')?
      (ON COMMIT (DELETE | PRESERVE) ROWS)? oid_clause? oid_index_clause?
      physical_properties? column_properties? table_partitioning_clauses?
      (CACHE | NOCACHE)? (RESULT_CACHE '(' MODE (DEFAULT | FORCE) ')')?
      parallel_clause? (ROWDEPENDENCIES | NOROWDEPENDENCIES)?
      (enable_disable_clause+)? row_movement_clause? flashback_archive_clause?
    ;

object_table_substitution
    : NOT? SUBSTITUTABLE AT ALL LEVELS
    ;

oid_clause
    : OBJECT IDENTIFIER IS (SYSTEM GENERATED | PRIMARY KEY)
    ;

oid_index_clause
    : OIDINDEX index_name? '(' (physical_attributes_clause | TABLESPACE tablespace)+ ')'
    ;

xmltype_table
    : OF XMLTYPE ('(' object_properties ')')?
         (XMLTYPE xmltype_storage)? xmlschema_spec? xmltype_virtual_columns?
         (ON COMMIT (DELETE | PRESERVE) ROWS)? oid_clause? oid_index_clause?
         physical_properties? column_properties? table_partitioning_clauses?
         (CACHE | NOCACHE)? (RESULT_CACHE '(' MODE (DEFAULT | FORCE) ')')?
         parallel_clause? (ROWDEPENDENCIES | NOROWDEPENDENCIES)?
	 (enable_disable_clause+)? row_movement_clause?
         flashback_archive_clause?
    ;

xmltype_virtual_columns
    : VIRTUAL COLUMNS '(' (','? column_name AS '(' expression ')')+ ')'
    ;

drop_table
    : DROP TABLE (IF EXISTS)? tableview_name PURGE?
    ;

alter_table
    : ALTER TABLE tableview_name
      (
      | alter_table_properties
      | constraint_clauses
      | column_clauses
//TODO      | alter_table_partitioning
//TODO      | alter_external_table
//      | move_table_clause
      )
//      ((enable_disable_clause | enable_or_disable (TABLE LOCK | ALL TRIGGERS) )+)?
    ;

alter_table_properties
    : alter_table_properties_1
    | RENAME TO tableview_name
    | shrink_clause
    | READ ONLY
    | READ WRITE
    | REKEY CHAR_STRING
    ;

alter_table_properties_1
    : ( physical_attributes_clause
      | logging_clause
      | table_compression
      | supplemental_table_logging
      | allocate_extent_clause
      | deallocate_unused_clause
      | (CACHE | NOCACHE)
      | RESULT_CACHE '(' MODE (DEFAULT | FORCE) ')'
      | upgrade_table_clause
      | records_per_block_clause
      | parallel_clause
      | row_movement_clause
      | flashback_archive_clause
      )+
      alter_iot_clauses?
    ;

supplemental_table_logging
    : ADD
       (','? SUPPLEMENTAL LOG  (supplemental_log_grp_clause | supplemental_id_key_clause) )*
    | DROP (','? SUPPLEMENTAL LOG (supplemental_id_key_clause | GROUP log_grp) )*
    ;

allocate_extent_clause
    : ALLOCATE EXTENT
       ( '(' ( SIZE size_clause
             | DATAFILE datafile=CHAR_STRING
             | INSTANCE inst_num=UNSIGNED_INTEGER
             )+
         ')'
       )?
    ;

deallocate_unused_clause
    : DEALLOCATE UNUSED (KEEP size_clause)?
    ;

upgrade_table_clause
    : UPGRADE (NOT? INCLUDING DATA) column_properties
    ;

records_per_block_clause
    : (MINIMIZE | NOMINIMIZE)? RECORDS_PER_BLOCK
    ;

alter_iot_clauses
    : index_org_table_clause
    | alter_overflow_clause
    | alter_mapping_table_clause
    | COALESCE
    ;

index_org_table_clause
    : (mapping_table_clause | PCTTHRESHOLD UNSIGNED_INTEGER | key_compression) index_org_overflow_clause?
    ;

mapping_table_clause
    : MAPPING TABLE
    | NOMAPPING
    ;

index_org_overflow_clause
    : (INCLUDING column_name)? OVERFLOW segment_attributes_clause?
    ;

alter_overflow_clause
    : add_overflow_clause
    | OVERFLOW (segment_attributes_clause | allocate_extent_clause | shrink_clause | deallocate_unused_clause)+
    ;

add_overflow_clause
    : ADD OVERFLOW segment_attributes_clause? ('(' (','? PARTITION segment_attributes_clause?)+  ')' )?
    ;

shrink_clause
    : SHRINK SPACE_KEYWORD COMPACT? CASCADE?
    ;

alter_mapping_table_clause
    : MAPPING TABLE (allocate_extent_clause | deallocate_unused_clause)
    ;

constraint_clauses
    : ADD '(' (out_of_line_constraint* | out_of_line_ref_constraint) ')'
    | ADD  (out_of_line_constraint* | out_of_line_ref_constraint)
    | MODIFY (CONSTRAINT constraint_name | PRIMARY KEY | UNIQUE paren_column_list)  constraint_state CASCADE?
    | RENAME CONSTRAINT old_constraint_name TO new_constraint_name
    | drop_constraint_clause+
    ;

old_constraint_name
    : constraint_name
    ;

new_constraint_name
    : constraint_name
    ;

drop_constraint_clause
    : DROP  drop_primary_key_or_unique_or_generic_clause
    ;

drop_primary_key_or_unique_or_generic_clause
    : (PRIMARY KEY | UNIQUE paren_column_list) CASCADE? (KEEP | DROP)?
    | CONSTRAINT constraint_name CASCADE?
    ;

column_clauses
    : add_modify_drop_column_clauses
    | rename_column_clause
    | modify_collection_retrieval
    | modify_lob_storage_clause
    ;

add_modify_drop_column_clauses
    : (add_column_clause
      | modify_column_clauses
      | alter_column_clause
      | drop_column_clause (',' drop_column_clause)*
      )+
    ;

add_column_clause
    : ADD COLUMN? ('(' (','? column_definition
              |','? virtual_column_definition
              )+
          ')'
          | ( column_definition | virtual_column_definition ))
       column_properties?
//TODO       (','? out_of_line_part_storage )
    ;

modify_column_clauses
    : MODIFY ('(' (','? modify_col_properties)+ ')'
             | modify_col_properties
             | modify_col_substitutable
             )
    ;

alter_column_clause
    : ALTER COLUMN? column_name
        (op=(SET | DROP) NOT NULL
        | TYPE datatype (USING (expression))?
        )
    ;

modify_col_properties
    : column_name datatype? (DEFAULT expression)? (ENCRYPT encryption_spec | DECRYPT)? inline_constraint* lob_storage_clause? //TODO alter_xmlschema_clause
    ;

modify_col_substitutable
    : COLUMN column_name NOT? SUBSTITUTABLE AT ALL LEVELS FORCE?
    ;

drop_column_clause
    : SET UNUSED (COLUMN names+=column_name| ('(' (','? names+=column_name)+ ')' )) (CASCADE CONSTRAINTS | INVALIDATE)*
    | DROP (COLUMN names+=column_name | '(' (','? names+=column_name)+ ')' ) (CASCADE CONSTRAINTS | INVALIDATE)* (CHECKPOINT UNSIGNED_INTEGER)?
    | DROP (UNUSED COLUMNS | COLUMNS CONTINUE) (CHECKPOINT UNSIGNED_INTEGER)
    ;

rename_column_clause
    : RENAME COLUMN? old_column_name TO new_column_name
    ;

old_column_name
    : column_name
    ;

new_column_name
    : column_name
    ;

modify_collection_retrieval
    : MODIFY NESTED TABLE collection_item RETURN AS (LOCATOR | VALUE)
    ;

collection_item
    : tableview_name
    ;

modify_lob_storage_clause
    : MODIFY LOB '(' lob_item ')' '(' modify_lob_parameters ')'
    ;

modify_lob_parameters
    : ( storage_clause
      | (PCTVERSION | FREEPOOLS) UNSIGNED_INTEGER
      | REBUILD FREEPOOLS
      | lob_retention_clause
      | lob_deduplicate_clause
      | lob_compression_clause
      | ENCRYPT encryption_spec
      | DECRYPT
      | CACHE
      | (CACHE | NOCACHE | CACHE READS) logging_clause?
      | allocate_extent_clause
      | shrink_clause
      | deallocate_unused_clause
     )+
    ;

// $<DDL -> SQL Statements for Stored PL/SQL Units

// $<Function DDLs

drop_function
    : DROP FUNCTION function_name
    ;

alter_function
    : ALTER FUNCTION function_name COMPILE DEBUG? compiler_parameters_clause* (REUSE SETTINGS)?
    ;

create_function_body
    : (CREATE (OR REPLACE)?)? FUNCTION function_name ('(' parameter (',' parameter)* ')')?
      RETURN type_spec (invoker_rights_clause|parallel_enable_clause|result_cache_clause|DETERMINISTIC)*
      ((PIPELINED? (IS | AS) (DECLARE? declare_spec* body | call_spec)) | (PIPELINED | AGGREGATE) USING implementation_type_name)
    ;

// $<Creation Function - Specific Clauses

parallel_enable_clause
    : PARALLEL_ENABLE partition_by_clause?
    ;

partition_by_clause
    : '(' PARTITION expression BY (ANY | (HASH | RANGE) '(' column_name (',' column_name)* ')')streaming_clause? ')'
    ;

result_cache_clause
    : RESULT_CACHE relies_on_part?
    ;

relies_on_part
    : RELIES_ON '(' tableview_name (',' tableview_name)* ')'
    ;

streaming_clause
    : (ORDER | CLUSTER) expression BY '(' column_name (',' column_name)* ')'
    ;

// $<Package DDLs

drop_package
    : DROP PACKAGE BODY? package_name
    ;

alter_package
    : ALTER PACKAGE package_name COMPILE DEBUG? (PACKAGE | BODY | SPECIFICATION)? compiler_parameters_clause* (REUSE SETTINGS)?
    ;

create_package
    : CREATE (OR REPLACE)? PACKAGE (package_spec | package_body)?
    ;

// $<Create Package - Specific Clauses

package_body
    : BODY package_name (IS | AS) package_obj_body* (BEGIN seq_of_statements | END package_name?)
    ;

package_spec
    : package_name invoker_rights_clause? (IS | AS) package_obj_spec* END package_name?
    ;

package_obj_spec
    : variable_declaration
    | subtype_declaration
    | cursor_declaration
    | exception_declaration
    | pragma_declaration
    | record_declaration
    | table_declaration
    | procedure_spec
    | function_spec
    ;

procedure_spec
    : PROCEDURE procedure_name ('(' parameter ( ',' parameter )* ')')? ';'
    ;

function_spec
    : FUNCTION function_name ('(' parameter ( ',' parameter)* ')')? RETURN type_spec (DETERMINISTIC)? (RESULT_CACHE)? ';'
    ;

package_obj_body
    : variable_declaration
    | subtype_declaration
    | cursor_declaration
    | exception_declaration
    | record_declaration
    | table_declaration
    | create_procedure_body
    | create_function_body
    | procedure_spec
    | function_spec
    ;

// $<Procedure DDLs

drop_procedure
    : DROP PROCEDURE procedure_name
    ;

alter_procedure
    : ALTER PROCEDURE procedure_name COMPILE DEBUG? compiler_parameters_clause* (REUSE SETTINGS)?
    ;

create_procedure_body
    : (CREATE (OR REPLACE)?)? PROCEDURE procedure_name ('(' parameter (',' parameter)* ')')?
      invoker_rights_clause? (IS | AS)
      (DECLARE? declare_spec* body | call_spec | EXTERNAL)
    ;

// $>

// $<Trigger DDLs

drop_trigger
    : DROP TRIGGER trigger_name
    ;

alter_trigger
    : ALTER TRIGGER tn1=trigger_name
      ((ENABLE | DISABLE) | RENAME TO tn2=trigger_name | COMPILE DEBUG? compiler_parameters_clause* (REUSE SETTINGS)?)
    ;

create_trigger
    : CREATE ( OR REPLACE )? TRIGGER trigger_name
    (simple_dml_trigger | compound_dml_trigger | non_dml_trigger)
    trigger_follows_clause? (ENABLE | DISABLE)? trigger_when_clause? trigger_body
    ;

trigger_follows_clause
    : FOLLOWS trigger_name (',' trigger_name)*
    ;

trigger_when_clause
    : WHEN '(' condition ')'
    ;

// $<Create Trigger- Specific Clauses
simple_dml_trigger
    : (BEFORE | AFTER | INSTEAD OF) dml_event_clause referencing_clause? for_each_row?
    ;

for_each_row
    : FOR EACH ROW
    ;

compound_dml_trigger
    : FOR dml_event_clause referencing_clause?
    ;

non_dml_trigger
    : (BEFORE | AFTER) non_dml_event (OR non_dml_event)* ON (DATABASE | (schema_name '.')? SCHEMA)
    ;

trigger_body
    : COMPOUND TRIGGER
    | CALL r_id
    | trigger_block
    ;

routine_clause
    : routine_name function_argument?
    ;

compound_trigger_block
    : COMPOUND TRIGGER declare_spec* timing_point_section+ END trigger_name
    ;

timing_point_section
    : bk=BEFORE STATEMENT IS trigger_block BEFORE STATEMENT ';'
    | bk=BEFORE EACH ROW IS trigger_block BEFORE EACH ROW ';'
    | ak=AFTER STATEMENT IS trigger_block AFTER STATEMENT ';'
    | ak=AFTER EACH ROW IS trigger_block AFTER EACH ROW ';'
    ;

non_dml_event
    : ALTER
    | ANALYZE
    | ASSOCIATE STATISTICS
    | AUDIT
    | COMMENT
    | CREATE
    | DISASSOCIATE STATISTICS
    | DROP
    | GRANT
    | NOAUDIT
    | RENAME
    | REVOKE
    | TRUNCATE
    | DDL
    | STARTUP
    | SHUTDOWN
    | DB_ROLE_CHANGE
    | LOGON
    | LOGOFF
    | SERVERERROR
    | SUSPEND
    | DATABASE
    | SCHEMA
    | FOLLOWS
    ;

dml_event_clause
    : dml_event_element (OR dml_event_element)* ON dml_event_nested_clause? tableview_name
    ;

dml_event_element
    : (DELETE|INSERT|UPDATE) (OF column_name (',' column_name)*)?
    ;

dml_event_nested_clause
    : NESTED TABLE tableview_name OF
    ;

referencing_clause
    : REFERENCING referencing_element+
    ;

referencing_element
    : (NEW | OLD | PARENT) column_alias
    ;

// $>
// $>

// $<Type DDLs

drop_type
    : DROP TYPE BODY? type_name (FORCE | VALIDATE)?
    ;

alter_type
    : ALTER TYPE type_name
    (compile_type_clause
    | replace_type_clause
    //TODO | {input.LT(2).getText().equalsIgnoreCase("attribute")}? alter_attribute_definition
    | alter_method_spec
    | alter_collection_clauses
    | modifier_clause
    ) dependent_handling_clause?
    ;

// $<Alter Type - Specific Clauses
compile_type_clause
    : COMPILE DEBUG? (SPECIFICATION | BODY)? compiler_parameters_clause* (REUSE SETTINGS)?
    ;

replace_type_clause
    : REPLACE invoker_rights_clause? AS OBJECT '(' object_member_spec (',' object_member_spec)* ')'
    ;

alter_method_spec
    : alter_method_element (',' alter_method_element)*
    ;

alter_method_element
    : (ADD|DROP) (map_order_function_spec | subprogram_spec)
    ;

alter_attribute_definition
    : (ADD | MODIFY | DROP) ATTRIBUTE (attribute_definition | '(' attribute_definition (',' attribute_definition)* ')')
    ;

attribute_definition
    : attribute_name type_spec?
    ;

alter_collection_clauses
    : MODIFY (LIMIT expression | ELEMENT TYPE type_spec)
    ;

dependent_handling_clause
    : INVALIDATE
    | CASCADE (CONVERT TO SUBSTITUTABLE | NOT? INCLUDING TABLE DATA)? dependent_exceptions_part?
    ;

dependent_exceptions_part
    : FORCE? EXCEPTIONS INTO tableview_name
    ;

create_type
    : CREATE (OR REPLACE)? TYPE (type_definition | type_body)
    ;

// $<Create Type - Specific Clauses
type_definition
    : type_name (OID CHAR_STRING)? object_type_def?
    ;

object_type_def
    : invoker_rights_clause? (object_as_part | object_under_part) sqlj_object_type?
      ('(' object_member_spec (',' object_member_spec)* ')')? modifier_clause*
    ;

object_as_part
    : (IS | AS) (OBJECT | varray_type_def | nested_table_type_def)
    ;

object_under_part
    : UNDER type_spec
    ;

nested_table_type_def
    : TABLE OF type_spec (NOT NULL)?
    ;

sqlj_object_type
    : EXTERNAL NAME expression LANGUAGE JAVA USING (SQLDATA|CUSTOMDATUM|ORADATA)
    ;

type_body
    : BODY type_name (IS | AS) (type_body_elements)+ END
    ;

type_body_elements
    : map_order_func_declaration
    | subprog_decl_in_type
    ;

map_order_func_declaration
    : (MAP | ORDER) MEMBER func_decl_in_type
    ;

subprog_decl_in_type
    : (MEMBER | STATIC) (proc_decl_in_type | func_decl_in_type | constructor_declaration)
    ;

proc_decl_in_type
    : PROCEDURE procedure_name '(' type_elements_parameter (',' type_elements_parameter)* ')'
      (IS | AS) (call_spec | DECLARE? declare_spec* body ';')
    ;

func_decl_in_type
    : FUNCTION function_name ('(' type_elements_parameter (',' type_elements_parameter)* ')')?
      RETURN type_spec (IS | AS) (call_spec | DECLARE? declare_spec* body ';')
    ;

constructor_declaration
    : FINAL? INSTANTIABLE? CONSTRUCTOR FUNCTION type_spec
      ('(' (SELF IN OUT type_spec ',') type_elements_parameter (',' type_elements_parameter)*  ')')?
      RETURN SELF AS RESULT (IS | AS) (call_spec | DECLARE? declare_spec* body ';')
    ;

// $>

// $<Common Type Clauses

modifier_clause
    : NOT? (INSTANTIABLE | FINAL | OVERRIDING)
    ;

object_member_spec
    : r_id type_spec sqlj_object_type_attr?
    | element_spec
    ;

sqlj_object_type_attr
    : EXTERNAL NAME expression
    ;

element_spec
    : modifier_clause? element_spec_options+ (',' pragma_clause)?
    ;

element_spec_options
    : subprogram_spec
    | constructor_spec
    | map_order_function_spec
    ;

subprogram_spec
    : (MEMBER|STATIC) (type_procedure_spec|type_function_spec)
    ;

type_procedure_spec
    : PROCEDURE procedure_name '(' type_elements_parameter (',' type_elements_parameter)* ')' ((IS | AS) call_spec)?
    ;

type_function_spec
    : FUNCTION function_name ('(' type_elements_parameter (',' type_elements_parameter)* ')')?
      RETURN (type_spec | SELF AS RESULT) ((IS | AS) call_spec | EXTERNAL VARIABLE? NAME expression)?
    ;

constructor_spec
    : FINAL? INSTANTIABLE? CONSTRUCTOR FUNCTION type_spec ('(' (SELF IN OUT type_spec ',') type_elements_parameter (',' type_elements_parameter)*  ')')?  RETURN SELF AS RESULT ((IS | AS) call_spec)?
    ;

map_order_function_spec
    : (MAP | ORDER) MEMBER type_function_spec
    ;

pragma_clause
    : PRAGMA RESTRICT_REFERENCES '(' pragma_elements (',' pragma_elements)* ')'
    ;

pragma_elements
    : r_id
    | DEFAULT
    ;

type_elements_parameter
    : parameter_name type_spec
    ;

// $<Sequence DDLs

drop_sequence
    : DROP SEQUENCE sequence_name
    ;

alter_sequence
    : ALTER SEQUENCE sequence_name sequence_spec+
    ;

create_sequence
    : CREATE SEQUENCE sequence_name (sequence_start_clause | sequence_spec)*
    ;

// $<Common Sequence

sequence_spec
    : INCREMENT BY UNSIGNED_INTEGER
    | MAXVALUE UNSIGNED_INTEGER
    | NOMAXVALUE
    | MINVALUE UNSIGNED_INTEGER
    | NOMINVALUE
    | CYCLE
    | NOCYCLE
    | CACHE UNSIGNED_INTEGER
    | NOCACHE
    | ORDER
    | NOORDER
    ;

sequence_start_clause
    : START WITH UNSIGNED_INTEGER
    ;

// $<Common DDL Clauses

invoker_rights_clause
    : AUTHID (CURRENT_USER|DEFINER)
    ;

compiler_parameters_clause
    : r_id '=' expression
    ;

call_spec
    : LANGUAGE (java_spec | c_spec)
    ;

// $<Call Spec - Specific Clauses

java_spec
    : JAVA NAME CHAR_STRING
    ;

c_spec
    : C_LETTER (NAME CHAR_STRING)? LIBRARY r_id c_agent_in_clause? (WITH CONTEXT)? c_parameters_clause?
    ;

c_agent_in_clause
    : AGENT IN '(' expression (',' expression)* ')'
    ;

c_parameters_clause
    : PARAMETERS '(' (expression (',' expression)* | '.' '.' '.') ')'
    ;

// $>

parameter
    : parameter_name (IN | OUT | INOUT | NOCOPY)* type_spec? default_value_part?
    ;

default_value_part
    : (ASSIGN_OP | DEFAULT) expression
    ;

// $<PL/SQL Elements Declarations

declare_spec
    : variable_declaration
    | subtype_declaration
    | cursor_declaration
    | exception_declaration
    | pragma_declaration
    | record_declaration
    | table_declaration
    | create_procedure_body
    | create_function_body
    ;

//incorporates constant_declaration
variable_declaration
    : variable_name CONSTANT? type_spec (NOT NULL)? default_value_part? ';'
    ;

subtype_declaration
    : SUBTYPE type_name IS type_spec (RANGE expression '..' expression)? (NOT NULL)? ';'
    ;

//cursor_declaration incorportates curscursor_body and cursor_spec
cursor_declaration
    : CURSOR cursor_name ('(' parameter_spec (',' parameter_spec)* ')' )? (RETURN type_spec)? (IS select_statement)? ';'
    ;

parameter_spec
    : parameter_name (IN? type_spec)? default_value_part?
    ;

exception_declaration
    : exception_name EXCEPTION ';'
    ;

pragma_declaration
    : PRAGMA (SERIALLY_REUSABLE
    | AUTONOMOUS_TRANSACTION
    | EXCEPTION_INIT '(' exception_name ',' numeric_negative ')'
    | INLINE '(' id1=r_id ',' expression ')'
    | RESTRICT_REFERENCES '(' (r_id | DEFAULT) (',' r_id)+ ')') ';'
    ;

record_declaration
    : record_type_dec
    | record_var_dec
    ;

// $<Record Declaration - Specific Clauses

//incorporates ref_cursor_type_definition
record_type_dec
    : TYPE type_name IS (RECORD '(' field_spec (',' field_spec)* ')' | REF CURSOR (RETURN type_spec)?) ';'
    ;

field_spec
    : column_name type_spec? (NOT NULL)? default_value_part?
    ;

record_var_dec
    : record_name type_name (PERCENT_ROWTYPE | PERCENT_TYPE) ';'
    ;

// $>

table_declaration
    : (table_type_dec | table_var_dec) ';'
    ;

table_type_dec
    : TYPE type_name IS (TABLE OF type_spec table_indexed_by_part? (NOT NULL)? | varray_type_def)
    ;

table_indexed_by_part
    : (idx1=INDEXED | idx2=INDEX) BY type_spec
    ;

varray_type_def
    : (VARRAY | VARYING ARRAY) '(' expression ')' OF type_spec (NOT NULL)?
    ;

table_var_dec
    : table_var_name type_spec
    ;

// $>

// $<PL/SQL Statements

seq_of_statements
    : (statement (';' | EOF) | label_declaration)+
    ;

label_declaration
    : ltp1= '<' '<' label_name '>' '>'
    ;

statement
    : CREATE swallow_to_semi
    | ALTER swallow_to_semi
    | GRANT ALL? swallow_to_semi
    | TRUNCATE swallow_to_semi
    | body
    | block
    | assignment_statement
    | continue_statement
    | exit_statement
    | goto_statement
    | if_statement
    | loop_statement
    | forall_statement
    | null_statement
    | raise_statement
    | return_statement
    | case_statement/*[true]*/
    | sql_statement
    | function_call
    ;

assignment_statement
    : (general_element | bind_variable) ASSIGN_OP expression
    ;

continue_statement
    : CONTINUE label_name? (WHEN condition)?
    ;

exit_statement
    : EXIT label_name? (WHEN condition)?
    ;

goto_statement
    : GOTO label_name
    ;

if_statement
    : IF condition THEN seq_of_statements elsif_part* else_part? END IF
    ;

elsif_part
    : ELSIF condition THEN seq_of_statements
    ;

else_part
    : ELSE seq_of_statements
    ;

loop_statement
    : label_name? (WHILE condition | FOR cursor_loop_param)? LOOP seq_of_statements END LOOP label_name?
    ;

// $<Loop - Specific Clause

cursor_loop_param
    : index_name IN REVERSE? lower_bound '..' upper_bound
    | record_name IN (cursor_name expression_list? | '(' select_statement ')')
    ;
// $>

forall_statement
    : FORALL index_name IN bounds_clause sql_statement (SAVE EXCEPTIONS)?
    ;

bounds_clause
    : lower_bound '..' upper_bound
    | INDICES OF collection_name between_bound?
    | VALUES OF index_name
    ;

between_bound
    : BETWEEN lower_bound AND upper_bound
    ;

lower_bound
    : concatenation
    ;

upper_bound
    : concatenation
    ;

null_statement
    : NULL
    ;

raise_statement
    : RAISE exception_name?
    ;

return_statement
    : RETURN condition?
    ;

function_call
    : CALL? routine_name function_argument?
    ;

body
    : BEGIN seq_of_statements (EXCEPTION exception_handler+)? END label_name?
    ;

// $<Body - Specific Clause

exception_handler
    : WHEN exception_name (OR exception_name)* THEN seq_of_statements
    ;

// $>

trigger_block
    : (DECLARE? declare_spec+)? body
    ;

block
    : DECLARE? declare_spec+ body
    ;

// $>

// $<SQL PL/SQL Statements

sql_statement
    : execute_immediate
    | data_manipulation_language_statements
    | cursor_manipulation_statements
    | transaction_control_statements
    ;

execute_immediate
    : EXECUTE IMMEDIATE expression (into_clause using_clause? | using_clause dynamic_returning_clause? | dynamic_returning_clause)?
    ;

// $<Execute Immediate - Specific Clause
dynamic_returning_clause
    : (RETURNING | RETURN) into_clause
    ;
// $>


// $<DML SQL PL/SQL Statements

data_manipulation_language_statements
    : merge_statement
    | lock_table_statement
    | select_statement
    | update_statement
    | delete_statement
    | insert_statement
    | explain_statement
    ;

// $>

// $<Cursor Manipulation SQL PL/SQL Statements

cursor_manipulation_statements
    : close_statement
    | open_statement
    | fetch_statement
    | open_for_statement
    ;

close_statement
    : CLOSE cursor_name
    ;

open_statement
    : OPEN cursor_name expression_list?
    ;

fetch_statement
    : FETCH cursor_name (it1=INTO variable_name (',' variable_name )* | BULK COLLECT INTO variable_name (',' variable_name )*)
    ;

open_for_statement
    : OPEN variable_name FOR (select_statement | expression) using_clause?
    ;

// $>

// $<Transaction Control SQL PL/SQL Statements

transaction_control_statements
    : set_transaction_command
    | set_constraint_command
    | commit_statement
    | rollback_statement
    | savepoint_statement
    ;

set_transaction_command
    : SET TRANSACTION
      (READ (ONLY | WRITE) | ISOLATION LEVEL (SERIALIZABLE | READ COMMITTED) | USE ROLLBACK SEGMENT rollback_segment_name)?
      (NAME quoted_string)?
    ;

set_constraint_command
    : SET (CONSTRAINT | CONSTRAINTS) (ALL | constraint_name (',' constraint_name)*) (IMMEDIATE | DEFERRED)
    ;

commit_statement
    : COMMIT WORK?
      (COMMENT expression | FORCE (CORRUPT_XID expression| CORRUPT_XID_ALL | expression (',' expression)?))?
      write_clause?
    ;

write_clause
    : WRITE (WAIT|NOWAIT)? (IMMEDIATE|BATCH)?
    ;

rollback_statement
    : ROLLBACK WORK? (TO SAVEPOINT? savepoint_name | FORCE quoted_string)?
    ;

savepoint_statement
    : SAVEPOINT savepoint_name
    ;

// Dml

/* TODO
//SHOULD BE OVERRIDEN!
compilation_unit
    :  seq_of_statements* EOF
    ;

//SHOULD BE OVERRIDEN!
seq_of_statements
    : select_statement
    | update_statement
    | delete_statement
    | insert_statement
    | lock_table_statement
    | merge_statement
    | explain_statement
//    | case_statement[true]
    ;
*/

explain_statement
    : EXPLAIN PLAN (SET STATEMENT_ID '=' quoted_string)? (INTO tableview_name)?
      FOR (select_statement | update_statement | delete_statement | insert_statement | merge_statement)
    ;

select_statement
    // MC-Note: a subquery should allow a full select_statement
    : subquery_factoring_clause? subquery
    ;

// $<Select - Specific Clauses
subquery_factoring_clause
    : WITH factoring_element (',' factoring_element)*
    ;

factoring_element
    : query_name paren_column_list? AS '(' subquery order_by_clause? ')'
      search_clause? cycle_clause?
    ;

search_clause
    : SEARCH (DEPTH | BREADTH) FIRST BY column_name ASC? DESC? (NULLS FIRST)? (NULLS LAST)?
      (',' column_name ASC? DESC? (NULLS FIRST)? (NULLS LAST)?)* SET column_name
    ;

cycle_clause
    : CYCLE column_name (',' column_name)* SET column_name TO expression DEFAULT expression
    ;

subquery
    : '(' subquery ')'                                                           # SubqueryParen
    | left=subquery op=subquery_operation_part right=subquery order_by_clause?   # SubqueryCompound
    | query_block                                                                # IgnoreSubquery
    ;

subquery_operation_part
    : (UNION | INTERSECT | EXCEPT | MINUS) ALL?
    ;

query_block
    : SELECT pref=(DISTINCT | UNIQUE | ALL)? (target_list+=selected_element (',' target_list+=selected_element)*)
      into_clause? from_clause? where_clause? hierarchical_query_clause? (group_by_clause | having_clause)* model_clause?
      (for_update_clause | order_by_clause | limit_clause)*
    ;

selected_element
    // TODO: need to figure out tableview_name for AST parsing
    : star                                  # Star1
    | dot_id '.' star                       # StarTable  // TODO, can '.' '*' be rolled into tableview_name?
    | tableview_name                        # IgnoreTableview_name
    | expr=expression alias=column_alias?   # Alias_expr
    ;

from_clause
    : FROM table_ref (',' table_ref)*
    ;

// NOTE to PIVOT clause
// according the SQL reference this should not be possible
// according to the reality it is. Here we probably apply pivot/unpivot onto whole join clause
// eventhough it is not enclosed in parenthesis. See pivot examples 09,10,11
table_ref_pivot
    : table_ref (pivot_clause | unpivot_clause)?
    ;

table_ref
    : table_ref join_clause                                     #JoinExpr
    | table_ref_aux flashback_query_clause*                     #TableRefSimple
    | table_ref_aux flashback_query_clause* table_alias?        #TableRefAux
    ;

table_ref_aux
    : dml_table_expression_clause (pivot_clause | unpivot_clause)?
    | ONLY '(' dml_table_expression_clause ')'
    ;

join_clause
    : query_partition_clause? join_type?
        JOIN table_ref query_partition_clause? (join_on_part | join_using_part)?
    ;

join_on_part
    : ON condition
    ;

join_using_part
    : USING '(' column_name (',' column_name)* ')'
    ;

join_type
    : CROSS
    | NATURAL? ( INNER |
                 (FULL | LEFT | RIGHT) OUTER? )
    ;

query_partition_clause
    : PARTITION BY ('(' subquery ')' | expression_list | expression (',' expression)*)
    ;

flashback_query_clause
    : VERSIONS BETWEEN (SCN | TIMESTAMP) expression
    | AS OF (SCN | TIMESTAMP | SNAPSHOT) expression
    ;

pivot_clause
    : PIVOT XML? '(' pivot_element (',' pivot_element)* pivot_for_clause pivot_in_clause ')'
    ;

pivot_element
    : aggregate_function_name '(' expression ')' column_alias?
    ;

pivot_for_clause
    : FOR (column_name | '(' column_name (',' column_name)* ')')
    ;

pivot_in_clause
    : IN '(' (subquery | ANY (',' ANY)* | pivot_in_clause_element (',' pivot_in_clause_element)*) ')'
    ;

pivot_in_clause_element
    : pivot_in_clause_elements column_alias?
    ;

pivot_in_clause_elements
    : expression
    | expression_list
    ;

unpivot_clause
    : UNPIVOT ((INCLUDE | EXCLUDE) NULLS)?
    '(' (column_name | '(' column_name (',' column_name)* ')') pivot_for_clause unpivot_in_clause ')'
    ;

unpivot_in_clause
    : IN '(' unpivot_in_elements (',' unpivot_in_elements)* ')'
    ;

unpivot_in_elements
    : (column_name | '(' column_name (',' column_name)* ')')
      (AS (constant | '(' constant (',' constant)* ')'))?
    ;

hierarchical_query_clause
    : CONNECT BY NOCYCLE? condition start_part?
    | start_part CONNECT BY NOCYCLE? condition
    ;

start_part
    : START WITH condition
    ;

group_by_clause
    : GROUP BY group_by_elements (',' group_by_elements)*
    ;

group_by_elements
    : grouping_sets_clause
    | rollup_cube_clause
    | expression
    ;

rollup_cube_clause
    : (ROLLUP|CUBE) '(' grouping_sets_elements (',' grouping_sets_elements)* ')'
    ;

grouping_sets_clause
    : GROUPING SETS '(' grouping_sets_elements (',' grouping_sets_elements)* ')'
    ;

grouping_sets_elements
    : rollup_cube_clause
    | expression_list
    | expression
    ;

having_clause
    : HAVING condition
    ;

model_clause
    : MODEL cell_reference_options* return_rows_clause? reference_model* main_model
    ;

cell_reference_options
    : (IGNORE | KEEP) NAV
    | UNIQUE (DIMENSION | SINGLE REFERENCE)
    ;

return_rows_clause
    : RETURN (UPDATED | ALL) ROWS
    ;

reference_model
    : REFERENCE reference_model_name ON '(' subquery ')' model_column_clauses cell_reference_options*
    ;

main_model
    : (MAIN main_model_name)? model_column_clauses cell_reference_options* model_rules_clause
    ;

model_column_clauses
    : model_column_partition_part? DIMENSION BY model_column_list MEASURES model_column_list
    ;

model_column_partition_part
    : PARTITION BY model_column_list
    ;

model_column_list
    : '(' model_column (',' model_column)*  ')'
    ;

model_column
    : expression table_alias?
    ;

model_rules_clause
    : model_rules_part? '(' model_rules_element (',' model_rules_element)* ')'
    ;

model_rules_part
    : RULES (UPDATE | UPSERT ALL?)? ((AUTOMATIC | SEQUENTIAL) ORDER)? model_iterate_clause?
    ;

model_rules_element
    : (UPDATE | UPSERT ALL?)? cell_assignment order_by_clause? '=' expression
    ;

cell_assignment
    : model_expression
    ;

model_iterate_clause
    : ITERATE '(' expression ')' until_part?
    ;

until_part
    : UNTIL '(' condition ')'
    ;

order_by_clause
    : ORDER SIBLINGS? BY order_by_elements (',' order_by_elements)*
    ;

order_by_elements
    : expression direction=(ASC | DESC)? (NULLS nulls=(FIRST | LAST))?
    ;

for_update_clause
    : FOR UPDATE for_update_of_part? for_update_options?
    ;

for_update_of_part
    : OF column_name (',' column_name)*
    ;

for_update_options
    : SKIP_ LOCKED
    | NOWAIT
    | WAIT expression
    ;

limit_clause
    : LIMIT expression
    ;

// $>

update_statement
    : UPDATE general_table_ref update_set_clause from_clause? where_clause? static_returning_clause? error_logging_clause?
    ;

// $<Update - Specific Clauses
update_set_clause
    : SET
      (column_based_update_set_clause (',' column_based_update_set_clause)*
      | VALUE '(' r_id ')' '=' expression  // todo: in postgres docs?
      )
    ;

column_based_update_set_clause
    : column_name '=' expression
    | paren_column_list '=' subquery
    ;

// $>

delete_statement
    : DELETE FROM? general_table_ref where_clause? static_returning_clause? error_logging_clause?
    ;

insert_statement
    : INSERT (single_table_insert | multi_table_insert)
    ;

// $<Insert - Specific Clauses

single_table_insert
    : insert_into_clause (values_clause static_returning_clause? | select_statement) error_logging_clause?
    ;

multi_table_insert
    : (ALL multi_table_element+ | conditional_insert_clause) select_statement
    ;

multi_table_element
    : insert_into_clause values_clause? error_logging_clause?
    ;

conditional_insert_clause
    : (ALL | FIRST)? conditional_insert_when_part+ conditional_insert_else_part?
    ;

conditional_insert_when_part
    : WHEN condition THEN multi_table_element+
    ;

conditional_insert_else_part
    : ELSE multi_table_element+
    ;

insert_into_clause
    : INTO general_table_ref paren_column_list?
    ;

values_clause
    : VALUES expression_list (',' expression_list)*
    ;

// $>
merge_statement
    : MERGE INTO tableview_name table_alias? USING selected_tableview ON '(' condition ')'
      (merge_update_clause merge_insert_clause? | merge_insert_clause merge_update_clause?)?
      error_logging_clause?
    ;

// $<Merge - Specific Clauses

merge_update_clause
    : WHEN MATCHED THEN UPDATE SET merge_element (',' merge_element)* where_clause? merge_update_delete_part?
    ;

merge_element
    : column_name '=' expression
    ;

merge_update_delete_part
    : DELETE where_clause
    ;

merge_insert_clause
    : WHEN NOT MATCHED THEN INSERT paren_column_list? VALUES expression_list where_clause?
    ;

selected_tableview
    : (tableview_name | '(' select_statement ')') table_alias?
    ;

// $>

lock_table_statement
    : LOCK TABLE lock_table_element (',' lock_table_element)* IN lock_mode MODE wait_nowait_part?
    ;

wait_nowait_part
    : WAIT expression
    | NOWAIT
    ;

// $<Lock - Specific Clauses

lock_table_element
    : tableview_name partition_extension_clause?
    ;

lock_mode
    : ROW SHARE
    | ROW EXCLUSIVE
    | SHARE UPDATE?
    | SHARE ROW EXCLUSIVE
    | EXCLUSIVE
    ;

// $<Common DDL Clauses

general_table_ref
    : (dml_table_expression_clause | ONLY '(' dml_table_expression_clause ')') table_alias?
    ;

static_returning_clause
    : (RETURNING | RETURN) expression (',' expression)* into_clause
    ;

error_logging_clause
    : LOG ERRORS error_logging_into_part? expression? error_logging_reject_part?
    ;

error_logging_into_part
    : INTO tableview_name
    ;

error_logging_reject_part
    : REJECT LIMIT (UNLIMITED | expression)
    ;

dml_table_expression_clause
    : table_collection_expression
    | '(' select_statement subquery_restriction_clause? ')'
    | tableview_name sample_clause?
    ;

table_collection_expression
    : (TABLE | THE) ('(' subquery ')' | '(' expression ')' ('(' '+' ')')?)
    ;

subquery_restriction_clause
    : WITH (READ ONLY | CHECK OPTION (CONSTRAINT constraint_name)?)
    ;

sample_clause
    : SAMPLE BLOCK? '(' expression (',' expression)? ')' seed_part?
    ;

seed_part
    : SEED '(' expression ')'
    ;

// $>

// $<Expression & Condition
cursor_expression
    : CURSOR '(' subquery ')'
    ;

expression_list
    : '(' expression? (',' expression)* ')'
    ;

condition
    : expression
    ;

expression
    : left=expression op=IS right=is_part                                             # IsExpr
    | left=expression NOT? op=IN ( '(' subquery ')' | expression_list )               # InExpr
    | left=expression NOT? op=BETWEEN right+=expression AND right+=expression         # BetweenExpr
    | left=expression NOT? op=like_type right+=expression (ESCAPE right+=expression)? # LikeExpr
    | left=expression op=relational_operator right=expression                 # RelExpr
    | left=expression op=(MEMBER | SUBMULTISET) OF? right=binary_expression   # MemberExpr
    | op=CURSOR expr=cursor_part                                              # CursorExpr
    | op=NOT expr=expression                                                  # NotExpr
    | left=expression op=AND right=expression                                 # AndExpr
    | left=expression op=OR  right=expression                                 # OrExpr
    | binary_expression                                                       # IgnoreExpr
    | '(' expression ')'                                                      # ParenExpr
    ;

is_part
    : NOT? (
        NULL | NAN | PRESENT | INFINITE | A_LETTER SET | EMPTY |
        OF TYPE? '(' ONLY? type_spec (',' type_spec)* ')'
        )
    ;

cursor_part
    : '(' subquery ')'
    ;

/*
logical_or_expression
    : logical_and_expression
    | logical_or_expression OR logical_and_expression
    ;

logical_and_expression
    : negated_expression
    | logical_and_expression AND negated_expression
    ;

negated_expression
    : NOT negated_expression
    | equality_expression
    ;
*/

multiset_type
    : MEMBER
    | SUBMULTISET
    ;

/*
equality_expression
    : multiset_expression (IS NOT?
      (NULL | NAN | PRESENT | INFINITE | A_LETTER SET | EMPTY | OF TYPE? '(' ONLY? type_spec (',' type_spec)* ')'))*
    ;

multiset_expression
    : relational_expression (multiset_type OF? concatenation)?
    ;

relational_expression
    : relational_expression relational_operator relational_expression
    | compound_expression
    ;

compound_expression
    : concatenation
    ;
*/

relational_operator
    : '=' | not_equal_op | '<' | '>' | less_than_or_equals_op | greater_than_or_equals_op
    ;

like_type
    : LIKE
    | LIKEC
    | LIKE2
    | LIKE4
    | ILIKE
    ;

like_escape_part
    : ESCAPE concatenation
    ;

between_elements
    : concatenation AND concatenation
    ;

concatenation
    // note that originally only included additive expressions...
    : binary_expression // (concatenation_op binary_expression)*
    ;

binary_expression
    // MC-Note: figure out topmost time expression...
    : binary_expression (AT (LOCAL | TIME ZONE binary_expression) | interval_expression)  # BinaryExpr
    | left=binary_expression op=('*' | '/' | '%') right=binary_expression            # BinaryExpr
    | left=binary_expression op=('+' | '-') right=binary_expression            # BinaryExpr
    | left=binary_expression op=CONCATENATION_OP right=binary_expression       # BinaryExpr
    | left=binary_expression op='@@' right=binary_expression                   # BinaryExpr
    | '(' binary_expression ')'                                                # ParenBinaryExpr
    | unary_expression                                                         # IgnoreBinaryExpr
    ;

/*
additive_expression
    : multiply_expression (op+=('+' | '-') multiply_expression)*
    ;

multiply_expression
    : datetime_expression (op+=('*' | '/') datetime_expression)*
    ;

datetime_expression
    : model_expression
      (AT (LOCAL | TIME ZONE concatenation) | interval_expression)?
    ;
*/

interval_expression
    : DAY ('(' concatenation ')')? TO SECOND ('(' concatenation ')')?
    | YEAR ('(' concatenation ')')? TO MONTH
    ;

model_expression
    : unary_expression '[' model_expression_element ']'
    ;

model_expression_element
    : (ANY | expression) (',' (ANY | expression))*
    | single_column_for_loop (',' single_column_for_loop)*
    | multi_column_for_loop
    ;

single_column_for_loop
    : FOR column_name
      (IN expression_list | for_like_part? FROM ex1=expression TO ex2=expression for_increment_decrement_type ex3=expression)
    ;

for_like_part
    : LIKE expression
    ;

for_increment_decrement_type
    : INCREMENT
    | DECREMENT
    ;

multi_column_for_loop
    : FOR
      '(' column_name (',' column_name)* ')' IN '(' (subquery | '(' expression_list (',' expression_list)* ')') ')'
    ;

unary_expression
    : unary_expression op='[' model_expression_element ']'      # UnaryExpr
    | op=('-' | '+') unary_expression                           # UnaryExpr
    | op=PRIOR unary_expression                                 # UnaryExpr
    | op=CONNECT_BY_ROOT unary_expression                       # UnaryExpr
    | op=NEW unary_expression                                   # UnaryExpr
    | op=DISTINCT unary_expression                              # UnaryExpr
    | op=ALL unary_expression                                   # UnaryExpr
    | case_statement                                            # IgnoreUnaryExpr
    | quantified_expression                                     # IgnoreUnaryExpr
    | standard_function                                         # IgnoreUnaryExpr
    | atom                                                      # IgnoreUnaryExpr
    ;

case_statement /*TODO [boolean isStatementParameter]
TODO scope    {
    boolean isStatement;
}
@init    {$case_statement::isStatement = $isStatementParameter;}*/
    : searched_case_statement
    | simple_case_statement
    ;

// $<CASE - Specific Clauses

simple_case_statement
    : label_name? ck1=CASE atom simple_case_when_part+  case_else_part? END CASE? label_name?
    ;

simple_case_when_part
    : WHEN whenExpr=expression THEN (/*TODO{$case_statement::isStatement}?*/ seq_of_statements | thenExpr=expression)
    ;

searched_case_statement
    : label_name? ck1=CASE searched_case_when_part+ case_else_part? END CASE? label_name?
    ;

searched_case_when_part
    : WHEN whenExpr=expression THEN (/*TODO{$case_statement::isStatement}?*/ seq_of_statements | thenExpr=expression)
    ;

case_else_part
    : ELSE (/*{$case_statement::isStatement}?*/ seq_of_statements | expression)
    ;
// $>

atom
    : table_element outer_join_sign
    | bind_variable
    | constant
    | literal
    | general_element
    | '(' atom ')'
    | ('(' subquery ')' | expression_list) // Note latter has mandatory parens also
    ;

expression_or_vector
    : expression (vector_expr)?
    ;

vector_expr
    : ',' expression (',' expression)*
    ;

quantified_expression
    : (SOME | EXISTS | ALL | ANY) ('(' subquery ')' | '(' expression ')')
    ;

standard_function
    : aggregate_windowed_function                                                                               #AggregateCall
    | regular_id function_argument_modeling using_clause?                                                       #TodoCall
    | (CAST | XMLCAST) '(' (MULTISET '(' subquery ')' | concatenation | expression) AS type_spec ')'            #CastCall
    | (subquery | atom) '::' type_spec                                                                          #CastCall
    | standard_function '::' type_spec                                                                          #CastCall
    | CHR '(' concatenation USING NCHAR_CS ')'                                                                  #TodoCall
    | COLLECT '(' (DISTINCT | UNIQUE)? concatenation collect_order_by_part? ')'                                 #TodoCall
    | name=within_or_over_clause_keyword function_argument within_or_over_part+                                 #WithinOrOverCall
    | DECOMPOSE '(' concatenation (CANONICAL | COMPATIBILITY)? ')'                                              #TodoCall
    | name=EXTRACT '(' (regular_id | expression) FROM concatenation ')'                                         #ExtractCall
    | (FIRST_VALUE | LAST_VALUE) function_argument_analytic respect_or_ignore_nulls? over_clause                #TodoCall
    | standard_prediction_function_keyword
      '(' expression (',' expression)* cost_matrix_clause? using_clause? ')'                                    #TodoCall
    | POSITION '(' expression IN expression ')'                                                                 #TodoCall
    | TRANSLATE '(' expression (USING (CHAR_CS | NCHAR_CS))? (',' expression)* ')'                              #TodoCall
    | TREAT '(' expression AS REF? type_spec ')'                                                                #TodoCall
    | TRIM '(' ((LEADING | TRAILING | BOTH)? quoted_string? FROM)? concatenation ')'                            #TodoCall
    | XMLAGG '(' expression order_by_clause? ')' ('.' general_element)?                                         #XmlCall
    | (XMLCOLATTVAL|XMLFOREST)
      '(' xml_multiuse_expression_element (',' xml_multiuse_expression_element)* ')' ('.' general_element)?     #XmlCall
    | XMLELEMENT
      '(' (ENTITYESCAPING | NOENTITYESCAPING)? (NAME | EVALNAME)? expression
       (/*TODO{input.LT(2).getText().equalsIgnoreCase("xmlattributes")}?*/ ',' xml_attributes_clause)?
       (',' expression column_alias?)* ')' ('.' general_element)?                                               #XmlCall
    | XMLEXISTS '(' expression xml_passing_clause? ')'                                                          #XmlCall
    | XMLPARSE '(' (DOCUMENT | CONTENT) concatenation WELLFORMED? ')' ('.' general_element)?                    #XmlCall
    | XMLPI
      '(' (NAME r_id | EVALNAME concatenation) (',' concatenation)? ')' ('.' general_element)?                  #XmlCall
    | XMLQUERY
      '(' concatenation xml_passing_clause? RETURNING CONTENT (NULL ON EMPTY)? ')' ('.' general_element)?       #XmlCall
    | XMLROOT
      '(' concatenation (',' xmlroot_param_version_part)? (',' xmlroot_param_standalone_part)? ')' ('.' general_element)? #XmlCall
    | XMLSERIALIZE
      '(' (DOCUMENT | CONTENT) concatenation (AS type_spec)?
      xmlserialize_param_enconding_part? xmlserialize_param_version_part? xmlserialize_param_ident_part? ((HIDE | SHOW) DEFAULTS)? ')'
      ('.' general_element)?                                                                                    #XmlCall
    | XMLTABLE
      '(' xml_namespaces_clause? concatenation xml_passing_clause? (COLUMNS xml_table_column (',' xml_table_column))? ')' ('.' general_element)?  #XmlCall
    ;

aggregate_windowed_function
    : over_clause_keyword function_argument_analytic over_clause?
    | COUNT '(' ( args=star | pref=(DISTINCT | UNIQUE | ALL)? concatenation) ')' over_clause?
    ;

over_clause_keyword
    : AVG
    | CORR
    | LAG
    | LEAD
    | MAX
    | MEDIAN
    | MIN
    | NTILE
    | RATIO_TO_REPORT
    | ROW_NUMBER
    | SUM
    | VARIANCE
    | REGR_
    | STDDEV
    | VAR_
    | COVAR_
    ;

/*TODO
stantard_function_enabling_using
    : {enablesUsingClause(input.LT(1).getText())}? REGULAR_ID
    ;
*/

within_or_over_clause_keyword
    : CUME_DIST
    | DENSE_RANK
    | LISTAGG
    | PERCENT_RANK
    | PERCENTILE_CONT
    | PERCENTILE_DISC
    | RANK
    ;

standard_prediction_function_keyword
    : PREDICTION
    | PREDICTION_BOUNDS
    | PREDICTION_COST
    | PREDICTION_DETAILS
    | PREDICTION_PROBABILITY
    | PREDICTION_SET
    ;

over_clause
    : OVER '(' query_partition_clause? (order_by_clause windowing_clause?)? ')'
    ;

windowing_clause
    : windowing_type
      (BETWEEN windowing_elements AND windowing_elements | windowing_elements)
    ;

windowing_type
    : ROWS
    | RANGE
    ;

windowing_elements
    : UNBOUNDED PRECEDING
    | CURRENT ROW
    | concatenation (PRECEDING|FOLLOWING)
    ;

using_clause
    : USING (star | using_element (',' using_element)*)
    ;

using_element
    : (IN OUT? | OUT)? selected_element column_alias?
    ;

collect_order_by_part
    : ORDER BY concatenation
    ;

within_or_over_part
    : WITHIN GROUP '(' order_by_clause ')'
    | over_clause
    ;

cost_matrix_clause
    : COST (MODEL AUTO? | '(' cost_class_name (',' cost_class_name)* ')' VALUES expression_list)
    ;

xml_passing_clause
    : PASSING (BY VALUE)? expression column_alias? (',' expression column_alias?)
    ;

xml_attributes_clause
    : XMLATTRIBUTES
     '(' (ENTITYESCAPING | NOENTITYESCAPING)? (SCHEMACHECK | NOSCHEMACHECK)?
     xml_multiuse_expression_element (',' xml_multiuse_expression_element)* ')'
    ;

xml_namespaces_clause
    : XMLNAMESPACES
      '(' (concatenation column_alias)? (',' concatenation column_alias)*
      xml_general_default_part? ')'
    ;

xml_table_column
    : xml_column_name
      (FOR ORDINALITY | type_spec (PATH concatenation)? xml_general_default_part?)
    ;

xml_general_default_part
    : DEFAULT concatenation
    ;

xml_multiuse_expression_element
    : expression (AS (id_expression | EVALNAME concatenation))?
    ;

xmlroot_param_version_part
    : VERSION (NO VALUE | expression)
    ;

xmlroot_param_standalone_part
    : STANDALONE (YES | NO VALUE?)
    ;

xmlserialize_param_enconding_part
    : ENCODING concatenation
    ;

xmlserialize_param_version_part
    : VERSION concatenation
    ;

xmlserialize_param_ident_part
    : NO INDENT
    | INDENT (SIZE '=' concatenation)?
    ;

// SqlPlus

sql_plus_command
    : ('/' | whenever_command | exit_command | prompt_command | set_command | show_errors_command)
    ;

whenever_command
    : WHENEVER (SQLERROR | OSERROR)
      (EXIT (SUCCESS | FAILURE | WARNING) (COMMIT | ROLLBACK) | CONTINUE (COMMIT|ROLLBACK|NONE))
    ;

set_command
    : SET regular_id (CHAR_STRING | ON | OFF | /*EXACT_NUM_LIT*/numeric | regular_id) // TODO
    ;

exit_command
    : EXIT
    ;

prompt_command
    : PROMPT
    ;

show_errors_command
    : SHOW ERR
    | SHOW ERRORS
    ;

// Common

partition_extension_clause
    : (SUBPARTITION | PARTITION) FOR? expression_list
    ;

column_alias
    : AS? (r_id | alias_quoted_string)
    | AS                                // TODO: remove?
    ;

table_alias
    : AS? (r_id | alias_quoted_string)
    ;

alias_quoted_string
    : quoted_string
    ;

where_clause
    : WHERE (current_of_clause | expression)
    ;

current_of_clause
    : CURRENT OF cursor_name
    ;

into_clause
    : INTO variable_name (',' variable_name)*
    | BULK COLLECT INTO variable_name (',' variable_name)*
    ;

// $>

// $<Common PL/SQL Named Elements

xml_column_name
    : r_id
    | quoted_string
    ;

cost_class_name
    : r_id
    ;

attribute_name
    : r_id
    ;

savepoint_name
    : r_id
    ;

rollback_segment_name
    : r_id
    ;

table_var_name
    : r_id
    ;

schema_name
    : r_id
    ;

routine_name
    : r_id ('.' id_expression)* ('@' link_name)?
    ;

package_name
    : r_id
    ;

implementation_type_name
    : r_id ('.' id_expression)?
    ;

parameter_name
    : r_id
    ;

reference_model_name
    : r_id
    ;

main_model_name
    : r_id
    ;

aggregate_function_name
    : r_id ('.' id_expression)*
    ;

query_name
    : r_id
    ;

constraint_name
    : r_id ('.' id_expression)* ('@' link_name)?
    ;

label_name
    : id_expression
    ;

type_name
    : id_expression ('.' id_expression)*
    ;

sequence_name
    : id_expression ('.' id_expression)*
    ;

exception_name
    : r_id ('.' id_expression)*
    ;

function_name
    : r_id ('.' id_expression)?
    ;

procedure_name
    : r_id ('.' id_expression)?
    ;

trigger_name
    : r_id ('.' id_expression)?
    ;

variable_name
    : dot_id
    | bind_variable
    ;

index_name
    : r_id
    ;

cursor_name
    : r_id
    | bind_variable
    ;

record_name
    : r_id
    | bind_variable
    ;

collection_name
    : r_id ('.' id_expression)?
    ;

link_name
    : r_id
    ;

column_name
    : r_id ('.' id_expression)*
    ;

role_name
    : r_id
    ;

tableview_name
    // MC-NOTE: if tables are always of form x.y, may want to replace r_id
    //          official parser seems to put linking under expressions
    : dot_id
      ('@' link_name | partition_extension_clause)?
    ;

dot_id
    : fields+=id_expression ('.' fields+=id_expression)*
    ;

star
    : '*'
    ;

// $>

// $<Common PL/SQL Specs

// NOTE: In reality this applies to aggregate functions only
keep_clause
    : KEEP '(' DENSE_RANK (FIRST | LAST) order_by_clause ')' over_clause?
    ;

function_argument
    : '(' argument_list+=argument? (',' argument_list+=argument )* ')' keep_clause?
    ;

function_argument_analytic
    : '(' (argument respect_or_ignore_nulls?)? (',' argument respect_or_ignore_nulls?)* ')' keep_clause?
    ;

function_argument_modeling
    : '(' column_name (',' (numeric | NULL) (',' (numeric | NULL))?)?
      USING (tableview_name '.' star | star | expression column_alias? (',' expression column_alias?)*)
      ')' keep_clause?
    ;

respect_or_ignore_nulls
    : (RESPECT | IGNORE) NULLS
    ;

argument
    : (r_id '=' '>')? expression
    ;

type_spec
    : datatype
    | REF? type_name (PERCENT_ROWTYPE | PERCENT_TYPE)?
    ;

datatype
    : native_datatype_element precision_part? (WITH LOCAL? TIME ZONE)?
    | INTERVAL (YEAR | DAY) ('(' expression ')')? TO (MONTH | SECOND) ('(' expression ')')?
    ;

precision_part
    : '(' numeric (',' numeric)? (CHAR | BYTE)? ')'
    ;

native_datatype_element
    : BINARY_INTEGER
    | PLS_INTEGER
    | NATURAL
    | BINARY_FLOAT
    | BINARY_DOUBLE
    | NATURALN
    | POSITIVE
    | POSITIVEN
    | SIGNTYPE
    | SIMPLE_INTEGER
    | NVARCHAR2
    | DEC
    | INTEGER
    | INT
    | NUMERIC
    | SMALLINT
    | NUMBER
    | DECIMAL
    | DOUBLE PRECISION?
    | FLOAT
    | REAL
    | NCHAR
    | LONG RAW?
    | CHAR
    | CHARACTER
    | VARCHAR2
    | VARCHAR
    | STRING
    | RAW
    | BOOLEAN
    | DATE
    | ROWID
    | UROWID
    | YEAR
    | MONTH
    | DAY
    | HOUR
    | MINUTE
    | SECOND
    | TIMEZONE_HOUR
    | TIMEZONE_MINUTE
    | TIMEZONE_REGION
    | TIMEZONE_ABBR
    | TIMESTAMP
    | TIMESTAMP_UNCONSTRAINED
    | TIMESTAMP_TZ_UNCONSTRAINED
    | TIMESTAMP_LTZ_UNCONSTRAINED
    | YMINTERVAL_UNCONSTRAINED
    | DSINTERVAL_UNCONSTRAINED
    | BFILE
    | BLOB
    | CLOB
    | NCLOB
    | MLSLABEL
    ;

bind_variable
    : (BINDVAR | ':' UNSIGNED_INTEGER)
      (INDICATOR? (BINDVAR | ':' UNSIGNED_INTEGER))?
      ('.' general_element)*
    ;

general_element
    : dot_id function_argument     # FuncCall
    | dot_id                       # Identifier
    ;

table_element
    : dot_id
    ;

// $>

// $<Lexer Mappings

constant
    : TIMESTAMP (quoted_string | bind_variable) (AT TIME ZONE quoted_string)?
    | INTERVAL (quoted_string | bind_variable | general_element)
      (DAY | HOUR | MINUTE | SECOND)
      ('(' (UNSIGNED_INTEGER | bind_variable) (',' (UNSIGNED_INTEGER | bind_variable) )? ')')?
      (TO ( DAY | HOUR | MINUTE | SECOND ('(' (UNSIGNED_INTEGER | bind_variable) ')')?))?
    | numeric
    | DATE quoted_string
    | quoted_string
    | NULL
    | TRUE
    | FALSE
    | DBTIMEZONE
    | SESSIONTIMEZONE
    | MINVALUE
    | MAXVALUE
    | DEFAULT
    ;

numeric
    : UNSIGNED_INTEGER
    | APPROXIMATE_NUM_LIT
    ;

numeric_negative
    : MINUS_SIGN numeric
    ;

quoted_string
    : CHAR_STRING
    //| CHAR_STRING_PERL
    | NATIONAL_CHAR_STRING_LIT
    ;

r_id
    : dot_id
    ;

id_expression
    : regular_id
    | DELIMITED_ID
    ;

not_equal_op
    : NOT_EQUAL_OP
    | '<' '>'
    | '!' '='
    | '^' '='
    ;

greater_than_or_equals_op
    : '>='
    | '>' '='
    ;

less_than_or_equals_op
    : '<='
    | '<' '='
    ;

concatenation_op
    : '||'
    | '|' '|'
    ;

outer_join_sign
    : '(' '+' ')'
    ;

regular_id
    : REGULAR_ID
    | A_LETTER
    | ADD
    | AFTER
    | AGENT
    | AGGREGATE
    //| ALL
    //| ALTER
    | ANALYZE
    //| AND
    //| ANY
    | ARRAY
    // | AS
    //| ASC
    | ASSOCIATE
    | AT
    | ATTRIBUTE
    | AUDIT
    | AUTHID
    | AUTO
    | AUTOMATIC
    | AUTONOMOUS_TRANSACTION
    | BATCH
    | BEFORE
    //| BEGIN
    // | BETWEEN
    | BFILE
    | BINARY_DOUBLE
    | BINARY_FLOAT
    | BINARY_INTEGER
    | BLOB
    | BLOCK
    | BODY
    | BOOLEAN
    | BOTH
    // | BREADTH
    | BULK
    | BUILD
    // | BY
    | BYTE
    | C_LETTER
    // | CACHE
    | CALL
    | CANONICAL
    | CASCADE
    //| CASE
    | CAST
    | CHAR
    | CHAR_CS
    | CHARACTER
    //| CHECK
    | CHR
    | CLOB
    | CLOSE
    | CLUSTER
    | COALESCE
    | COLLECT
    | COLUMNS
    | COMMENT
    | COMMIT
    | COMMITTED
    | COMPATIBILITY
    | COMPILE
    | COMPLETE
    | COMPOUND
    //| CONNECT
    //| CONNECT_BY_ROOT
    | CONCAT
    | CONSTANT
    | CONSTRAINT
    | CONSTRAINTS
    | CONSTRUCTOR
    | CONTENT
    | CONTEXT
    | CONTINUE
    | CONVERT
    | CORRUPT_XID
    | CORRUPT_XID_ALL
    | COST
    | COUNT
    //| CREATE
    | CROSS
    | CUBE
    //| CURRENT
    | CURRENT_USER
    | CURSOR
    | CUSTOMDATUM
    | CYCLE
    | DATA
    | DATABASE
    | DATE
    | DAY
    | DB_ROLE_CHANGE
    | DBTIMEZONE
    | DDL
    | DEBUG
    | DEC
    | DECIMAL
    //| DECLARE
    | DECODE
    | DECOMPOSE
    | DECREMENT
    //| DEFAULT
    | DEFAULTS
    | DEFERRED
    | DEFINER
    // | DELETE
    // | DEPTH
    //| DESC
    | DEMAND
    | DETERMINISTIC
    | DIMENSION
    | DISABLE
    | DISASSOCIATE
    //| DISTINCT
    | DOCUMENT
    | DOUBLE
    //| DROP
    | DSINTERVAL_UNCONSTRAINED
    | EACH
    | EDITIONING
    | ELEMENT
    //| ELSE
    //| ELSIF
    | EMPTY
    | ENABLE
    | ENCODING
    //| END
    | ENFORCED
    | ENTITYESCAPING
    | ERR
    | ERRORS
    | ESCAPE
    | EVALNAME
    | EXCEPTION
    | EXCEPTION_INIT
    | EXCEPTIONS
    | EXCLUDE
    //| EXCLUSIVE
    | EXECUTE
    //| EXISTS
    | EXIT
    | EXPLAIN
    | EXTERNAL
    | EXTRACT
    | FAILURE
    //| FALSE
    //| FETCH
    | FAST
    | FINAL
    | FIRST
    | FIRST_VALUE
    | FLOAT
    | FOLLOWING
    | FOLLOWS
    //| FOR
    | FORALL
    | FORCE
    // | FROM
    | FULL
    | FUNCTION
    //| GOTO
    //| GRANT
    //| GROUP
    | GROUPING
    | HASH
    //| HAVING
    | HIDE
    | HOUR
    //| IF
    | IGNORE
    | IMMEDIATE
    // | IN
    | INCLUDE
    | INCLUDING
    | INCREMENT
    | INDENT
    //| INDEX
    | INDEXED
    | INDICATOR
    | INDICES
    | INFINITE
    | INLINE
    | INNER
    | INOUT
    //| INSERT
    | INSTANTIABLE
    | INSTEAD
    | INT
    | INTEGER
    //| INTERSECT
    | INTERVAL
    // | INTO
    | INVALIDATE
    //| IS
    | ISOLATION
    | ITERATE
    | JAVA
    | JOIN
    | KEEP
    | LANGUAGE
    | LAST
    | LAST_VALUE
    | LEADING
    | LEFT
    | LEVEL
    | LIBRARY
    // | LIKE
    | LIKE2
    | LIKE4
    | LIKEC
    | LIMIT
    | LIST
    | LOCAL
    //| LOCK
    | LOCKED
    | LOG
    | LOGOFF
    | LOGON
    | LONG
    | LOOP
    | MAIN
    | MAP
    | MASTER
    | MATCHED
    | MAXVALUE
    | MEASURES
    | MEMBER
    | MERGE
    //| MINUS
    | MINUTE
    | MINVALUE
    | MLSLABEL
    //| MODE
    | MODEL
    | MODIFY
    | MONTH
    | MULTISET
    | NAME
    | NAN
    | NATURAL
    | NATURALN
    | NAV
    | NCHAR
    | NCHAR_CS
    | NCLOB
    | NESTED
    | NEVER
    | NEW
    | NO
    | NOAUDIT
    // | NOCACHE
    | NOCOPY
    | NOCYCLE
    | NOENTITYESCAPING
    //| NOMAXVALUE
    //| NOMINVALUE
    | NONE
    // | NOORDER
    | NOSCHEMACHECK
    //| NOT
    //| NOWAIT
    // | NULL
    | NULLS
    | NUMBER
    | NUMERIC
    | NVARCHAR2
    | NVL
    | MATERIALIZED
    | OBJECT
    //| OF
    | OFF
    | OID
    | OLD
    //| ON
    | ONLY
    | OPEN
    //| OPTION
    //| OR
    | ORADATA
    //| ORDER
    | ORDINALITY
    | OSERROR
    | OUT
    | OUTER
    | OVER
    | OVERRIDING
    | PACKAGE
    | PARALLEL_ENABLE
    | PARAMETERS
    | PARENT
    | PARTITION
    | PASSING
    | PATH
    //| PERCENT_ROWTYPE
    //| PERCENT_TYPE
    | PIPELINED
    //| PIVOT
    | PLAN
    | PLS_INTEGER
    | POSITIVE
    | POSITIVEN
    | PRAGMA
    | PREBUILT
    | PRECEDING
    | PRECISION
    | PRESENT
    //| PRIOR
    //| PROCEDURE
    | RAISE
    | RANGE
    | RAW
    | READ
    | REAL
    | RECORD
    | REDUCED
    | REF
    | REFERENCE
    | REFERENCING
    | REFRESH
    | REJECT
    | RELIES_ON
    | RENAME
    | REPLACE
    | RESPECT
    | RESTRICT_REFERENCES
    | RESULT
    | RESULT_CACHE
    | RETURN
    | RETURNING
    | REUSE
    | REVERSE
    | REWRITE
    //| REVOKE
    | RIGHT
    | ROLE
    | ROLLBACK
    | ROLLUP
    | ROW
    | ROWID
    | ROWS
    | RULES
    | SAMPLE
    | SAVE
    | SAVEPOINT
    | SCHEMA
    | SCHEMACHECK
    | SCN
    // | SEARCH
    | SECOND
    | SEED
    | SEGMENT
    // | SELECT
    | SELF
    // | SEQUENCE
    | SEQUENTIAL
    | SERIALIZABLE
    | SERIALLY_REUSABLE
    | SERVERERROR
    | SESSIONTIMEZONE
    | SET
    | SETS
    | SETTINGS
    //| SHARE
    | SHOW
    | SHUTDOWN
    | SIBLINGS
    | SIGNTYPE
    | SIMPLE_INTEGER
    | SINGLE
    | SIZE
    | SKIP_
    | SMALLINT
    | SNAPSHOT
    | SOME
    | SPECIFICATION
    | SQLDATA
    | SQLERROR
    | STANDALONE
    //| START
    | STARTUP
    | STATEMENT
    | STATEMENT_ID
    | STATIC
    | STATISTICS
    | STRING
    | SUBMULTISET
    | SUBPARTITION
    | SUBSTITUTABLE
    | SUBSTRING
    | SUBTYPE
    | SUCCESS
    | SUSPEND
    //| TABLE
    | TABLES
    //| THE
    //| THEN
    | TIME
    | TIMESTAMP
    | TIMESTAMP_LTZ_UNCONSTRAINED
    | TIMESTAMP_TZ_UNCONSTRAINED
    | TIMESTAMP_UNCONSTRAINED
    | TIMEZONE_ABBR
    | TIMEZONE_HOUR
    | TIMEZONE_MINUTE
    | TIMEZONE_REGION
    //| TO
    | TO_CHAR
    | TO_DATE
    | TRAILING
    | TRANSACTION
    | TRANSLATE
    | TREAT
    | TRIGGER
    | TRIM
    //| TRUE
    | TRUNCATE
    | TRUSTED
    | TYPE
    | UNBOUNDED
    | UNDER
    //| UNION
    //| UNIQUE
    | UNLIMITED
    //| UNPIVOT
    | UNTIL
    //| UPDATE
    | UPDATED
    | UPSERT
    | UROWID
    | USE
    //| USING
    | VALIDATE
    | VALUE
    //| VALUES
    | VARCHAR
    | VARCHAR2
    | VARIABLE
    | VARRAY
    | VARYING
    | VERBOSE
    | VERSION
    | VERSIONS
    | VIEW
    | WAIT
    | WARNING
    | WELLFORMED
    // | WHEN
    | WHENEVER
    // | WHERE
    | WHILE
    //| WITH
    | WITHIN
    | WITHOUT
    | WORK
    | WRITE
    | XML
    | XMLAGG
    | XMLATTRIBUTES
    | XMLCAST
    | XMLCOLATTVAL
    | XMLELEMENT
    | XMLEXISTS
    | XMLFOREST
    | XMLNAMESPACES
    | XMLPARSE
    | XMLPI
    | XMLQUERY
    | XMLROOT
    | XMLSERIALIZE
    | XMLTABLE
    | YEAR
    | YES
    | YMINTERVAL_UNCONSTRAINED
    | ZONE
    | PREDICTION
    | PREDICTION_BOUNDS
    | PREDICTION_COST
    | PREDICTION_DETAILS
    | PREDICTION_PROBABILITY
    | PREDICTION_SET
    | PUBLIC
    | CUME_DIST
    | DENSE_RANK
    | LISTAGG
    | PERCENT_RANK
    | PERCENTILE_CONT
    | PERCENTILE_DISC
    | RANK
    | AVG
    | CORR
    | LAG
    | LEAD
    | MAX
    | MEDIAN
    | MIN
    | NTILE
    | RATIO_TO_REPORT
    | ROW_NUMBER
    | SUM
    | VARIANCE
    | REGR_
    | STDDEV
    | VAR_
    | COVAR_
    ;

A_LETTER:                     A;
ADD:                          A D D;
AFTER:                        A F T E R;
AGENT:                        A G E N T;
AGGREGATE:                    A G G R E G A T E;
ALL:                          A L L;
ALLOCATE:                     A L L O C A T E;
ALLOW:                        A L L O W;
ALTER:                        A L T E R;
ALWAYS:                       A L W A Y S;
ANALYZE:                      A N A L Y Z E;
AND:                          A N D;
ANY:                          A N Y;
ANYSCHEMA:                    A N Y S C H E M A;
ARCHIVE:                      A R C H I V E;
ARRAY:                        A R R A Y;
AS:                           A S;
ASC:                          A S C;
ASSOCIATE:                    A S S O C I A T E;
AT:                           A T;
ATTRIBUTE:                    A T T R I B U T E;
AUDIT:                        A U D I T;
AUTHID:                       A U T H I D;
AUTO:                         A U T O;
AUTOMATIC:                    A U T O M A T I C;
AUTONOMOUS_TRANSACTION:       A U T O N O M O U S '_' T R A N S A C T I O N;
BASIC:                        B A S I C;
BASICFILE:                    B A S I C F I L E;
BATCH:                        B A T C H;
BEFORE:                       B E F O R E;
BEGIN:                        B E G I N;
BETWEEN:                      B E T W E E N;
BFILE:                        B F I L E;
BINARY:                       B I N A R Y;
BINARY_DOUBLE:                B I N A R Y '_' D O U B L E;
BINARY_FLOAT:                 B I N A R Y '_' F L O A T;
BINARY_INTEGER:               B I N A R Y '_' I N T E G E R;
BITMAP:                       B I T M A P;
BUFFER_POOL:                  B U F F E R '_' P O O L;
BUILD:                        B U I L D;
BLOB:                         B L O B;
BLOCK:                        B L O C K;
BODY:                         B O D Y;
BOOLEAN:                      B O O L E A N;
BOTH:                         B O T H;
BREADTH:                      B R E A D T H;
BULK:                         B U L K;
BY:                           B Y;
BYTE:                         B Y T E;
C_LETTER:                     C;
CACHE:                        C A C H E;
CALL:                         C A L L;
CANONICAL:                    C A N O N I C A L;
CASCADE:                      C A S C A D E;
CASE:                         C A S E;
CAST:                         C A S T;
CHAR:                         C H A R;
CHAR_CS:                      C H A R '_' C S;
CHARACTER:                    C H A R A C T E R;
CHECK:                        C H E C K;
CHECKPOINT:                   C H E C K P O I N T;
CHR:                          C H R;
CHUNK:                        C H U N K;
CLOB:                         C L O B;
CLOSE:                        C L O S E;
CLUSTER:                      C L U S T E R;
COALESCE:                     C O A L E S C E;
COLLECT:                      C O L L E C T;
COLUMN:                       C O L U M N;
COLUMNS:                      C O L U M N S;
COLUMN_VALUE:                 C O L U M N '_' V A L U E;
COMMENT:                      C O M M E N T;
COMMIT:                       C O M M I T;
COMMITTED:                    C O M M I T T E D;
COMPACT:                      C O M P A C T;
COMPATIBILITY:                C O M P A T I B I L I T Y;
COMPILE:                      C O M P I L E;
COMPLETE:                     C O M P L E T E;
COMPOUND:                     C O M P O U N D;
COMPRESS:                     C O M P R E S S;
CONCAT:                       C O N C A T;
CONNECT:                      C O N N E C T;
CONNECT_BY_ROOT:              C O N N E C T '_' B Y '_' R O O T;
CONSTANT:                     C O N S T A N T;
CONSTRAINT:                   C O N S T R A I N T;
CONSTRAINTS:                  C O N S T R A I N T S;
CONSTRUCTOR:                  C O N S T R U C T O R;
CONTENT:                      C O N T E N T;
CONTEXT:                      C O N T E X T;
CONTINUE:                     C O N T I N U E;
CONVERT:                      C O N V E R T;
CORRUPT_XID:                  C O R R U P T '_' X I D;
CORRUPT_XID_ALL:              C O R R U P T '_' X I D '_' A L L;
COST:                         C O S T;
COUNT:                        C O U N T;
CREATE:                       C R E A T E;
CREATEDB:                     C R E A T E D B;
CREATEROLE:                   C R E A T E R O L E;
CREATION:                     C R E A T I O N;
CROSS:                        C R O S S;
CUBE:                         C U B E;
CURRENT:                      C U R R E N T;
CURRENT_USER:                 C U R R E N T '_' U S E R;
CURSOR:                       C U R S O R;
CUSTOMDATUM:                  C U S T O M D A T U M;
CYCLE:                        C Y C L E;
DATA:                         D A T A;
DATABASE:                     D A T A B A S E;
DATAFILE:                     D A T A F I L E;
DATE:                         D A T E;
DAY:                          D A Y;
DB_ROLE_CHANGE:               D B '_' R O L E '_' C H A N G E;
DBTIMEZONE:                   D B T I M E Z O N E;
DDL:                          D D L;
DEBUG:                        D E B U G;
DEALLOCATE:                   D E A L L O C A T E;
DEC:                          D E C;
DECIMAL:                      D E C I M A L;
DECLARE:                      D E C L A R E;
DECODE:                       D E C O D E;
DECOMPOSE:                    D E C O M P O S E;
DECREMENT:                    D E C R E M E N T;
DECRYPT:                      D E C R Y P T;
DEDUPLICATE:                  D E D U P L I C A T E;
DEFAULT:                      D E F A U L T;
DEFAULTS:                     D E F A U L T S;
DEFERRABLE:                   D E F E R R A B L E;
DEFERRED:                     D E F E R R E D;
DEFINER:                      D E F I N E R;
DELETE:                       D E L E T E;
DEMAND:                       D E M A N D;
DEPTH:                        D E P T H;
DESC:                         D E S C;
DETERMINISTIC:                D E T E R M I N I S T I C;
DIMENSION:                    D I M E N S I O N;
DISABLE:                      D I S A B L E;
DISALLOW:                     D I S A L L O W;
DISASSOCIATE:                 D I S A S S O C I A T E;
DISTINCT:                     D I S T I N C T;
DOCUMENT:                     D O C U M E N T;
DOUBLE:                       D O U B L E;
DROP:                         D R O P;
DSINTERVAL_UNCONSTRAINED:     D S I N T E R V A L '_' U N C O N S T R A I N E D;
EACH:                         E A C H;
EDITIONING:                   E D I T I O N I N G;
ELEMENT:                      E L E M E N T;
ELSE:                         E L S E;
ELSIF:                        E L S I F;
EMPTY:                        E M P T Y;
ENABLE:                       E N A B L E;
ENCODING:                     E N C O D I N G;
ENCRYPT:                      E N C R Y P T;
END:                          E N D;
ENFORCED:                     E N F O R C E D;
ENTITYESCAPING:               E N T I T Y E S C A P I N G;
ERR:                          E R R;
ERRORS:                       E R R O R S;
ESCAPE:                       E S C A P E;
EVALNAME:                     E V A L N A M E;
EXCEPT:                       E X C E P T;
EXCEPTION:                    E X C E P T I O N;
EXCEPTION_INIT:               E X C E P T I O N '_' I N I T;
EXCEPTIONS:                   E X C E P T I O N S;
EXCLUDE:                      E X C L U D E;
EXCLUSIVE:                    E X C L U S I V E;
EXECUTE:                      E X E C U T E;
EXISTS:                       E X I S T S;
EXIT:                         E X I T;
EXPLAIN:                      E X P L A I N;
EXTENT:                       E X T E N T;
EXTERNAL:                     E X T E R N A L;
EXTRACT:                      E X T R A C T;
FAILURE:                      F A I L U R E;
FALSE:                        F A L S E;
FAST:                         F A S T;
FETCH:                        F E T C H;
FILESYSTEM_LIKE_LOGGING:      F I L E S Y S T E M '_' L I K E '_' L O G G I N G;
FINAL:                        F I N A L;
FIRST:                        F I R S T;
FIRST_VALUE:                  F I R S T '_' V A L U E;
FLASHBACK:                    F L A S H B A C K;
FLASH_CACHE:                  F L A S H '_' C A C H E;
FLOAT:                        F L O A T;
FOLLOWING:                    F O L L O W I N G;
FOLLOWS:                      F O L L O W S;
FOR:                          F O R;
FORALL:                       F O R A L L;
FORCE:                        F O R C E;
FOREIGN:                      F O R E I G N;
FREELIST:                     F R E E L I S T;
FREELISTS:                    F R E E L I S T S;
FREEPOOLS:                    F R E E P O O L S;
FROM:                         F R O M;
FULL:                         F U L L;
FUNCTION:                     F U N C T I O N;
GENERATED:                    G E N E R A T E D;
GLOBAL:                       G L O B A L;
GOTO:                         G O T O;
GRANT:                        G R A N T;
GROUP:                        G R O U P;
GROUPS:                       G R O U P S;
GROUPING:                     G R O U P I N G;
HASH:                         H A S H;
HAVING:                       H A V I N G;
HIDE:                         H I D E;
HIGH:                         H I G H;
HOUR:                         H O U R;
IDENTIFIED:                   I D E N T I F I E D;
IDENTIFIER:                   I D E N T I F I E R;
IF:                           I F;
IGNORE:                       I G N O R E;
ILIKE:                        I L I K E;
IMMEDIATE:                    I M M E D I A T E;
IN:                           I N;
INCLUDE:                      I N C L U D E;
INCLUDING:                    I N C L U D I N G;
INCREMENT:                    I N C R E M E N T;
INDENT:                       I N D E N T;
INDEX:                        I N D E X;
INDEXED:                      I N D E X E D;
INDEXTYPE:                    I N D E X T Y P E;
INDICATOR:                    I N D I C A T O R;
INDICES:                      I N D I C E S;
INFINITE:                     I N F I N I T E;
INITIAL:                      I N I T I A L;
INITIALLY:                    I N I T I A L L Y;
INITRANS:                     I N I T R A N S;
INLINE:                       I N L I N E;
INNER:                        I N N E R;
INOUT:                        I N O U T;
INSERT:                       I N S E R T;
INSTANCE:                     I N S T A N C E;
INSTANTIABLE:                 I N S T A N T I A B L E;
INSTEAD:                      I N S T E A D;
INT:                          I N T;
INTEGER:                      I N T E G E R;
INTERSECT:                    I N T E R S E C T;
INTERVAL:                     I N T E R V A L;
INTO:                         I N T O;
INVALIDATE:                   I N V A L I D A T E;
INVISIBLE:                    I N V I S I B L E;
IS:                           I S;
ISOLATION:                    I S O L A T I O N;
ITERATE:                      I T E R A T E;
JAVA:                         J A V A;
JOIN:                         J O I N;
KEEP:                         K E E P;
KEEP_DUPLICATES:              K E E P '_' D U P L I C A T E S;
KEY:                          K E Y;
LANGUAGE:                     L A N G U A G E;
LAST:                         L A S T;
LAST_VALUE:                   L A S T '_' V A L U E;
LEADING:                      L E A D I N G;
LEFT:                         L E F T;
LESS:                         L E S S;
LEVEL:                        L E V E L;
LEVELS:                       L E V E L S;
LIBRARY:                      L I B R A R Y;
LIKE:                         L I K E;
LIKE2:                        L I K E '2';
LIKE4:                        L I K E '4';
LIKEC:                        L I K E C;
LIMIT:                        L I M I T;
LIST:                         L I S T;
LOCAL:                        L O C A L;
LOB:                          L O B;
LOBS:                         L O B S;
LOCATOR:                      L O C A T O R;
LOCK:                         L O C K;
LOCKED:                       L O C K E D;
LOG:                          L O G;
LOGGING:                      L O G G I N G;
LOGOFF:                       L O G O F F;
LOGIN:                        L O G I N;
LOGON:                        L O G O N;
LONG:                         L O N G;
LOOP:                         L O O P;
LOW:                          L O W;
MAIN:                         M A I N;
MAP:                          M A P;
MAPPING:                      M A P P I N G;
MASTER:                       M A S T E R;
MATCHED:                      M A T C H E D;
MAXEXTENTS:                   M A X E X T E N T S;
MAXVALUE:                     M A X V A L U E;
MEASURES:                     M E A S U R E S;
MEDIUM:                       M E D I U M;
MEMBER:                       M E M B E R;
MERGE:                        M E R G E;
MINEXTENTS:                   M I N E X T E N T S;
MINIMIZE:                     M I N I M I Z E;
MINUS:                        M I N U S;
MINUTE:                       M I N U T E;
MINVALUE:                     M I N V A L U E;
MLSLABEL:                     M L S L A B E L;
MODE:                         M O D E;
MODEL:                        M O D E L;
MODIFY:                       M O D I F Y;
MONTH:                        M O N T H;
MOVEMENT:                     M O V E M E N T;
MULTISET:                     M U L T I S E T;
NAME:                         N A M E;
NAN:                          N A N;
NATURAL:                      N A T U R A L;
NATURALN:                     N A T U R A L N;
NAV:                          N A V;
NCHAR:                        N C H A R;
NCHAR_CS:                     N C H A R '_' C S;
NCLOB:                        N C L O B;
NESTED:                       N E S T E D;
NEVER:                        N E V E R;
NEW:                          N E W;
NEXT:                         N E X T;
NO:                           N O;
NOAUDIT:                      N O A U D I T;
NOCACHE:                      N O C A C H E;
NOCOMPRESS:                   N O C O M P R E S S;
NOCOPY:                       N O C O P Y;
NOCYCLE:                      N O C Y C L E;
NOENTITYESCAPING:             N O E N T I T Y E S C A P I N G;
NOLOGGING:                    N O L O G G I N G;
NOMAPPING:                    N O M A P P I N G;
NOMAXVALUE:                   N O M A X V A L U E;
NOMINIMIZE:                   N O M I N I M I Z E;
NOMINVALUE:                   N O M I N V A L U E;
NONE:                         N O N E;
NONSCHEMA:                    N O N S C H E M A;
NOORDER:                      N O O R D E R;
NOPARALLEL:                   N O P A R A L L E L;
NORELY:                       N O R E L Y;
NOROWDEPENDENCIES:            N O R O W D E P E N D E N C I E S;
NOSCHEMACHECK:                N O S C H E M A C H E C K;
NOSORT:                       N O S O R T;
NOT:                          N O T;
NOVALIDATE:                   N O V A L I D A T E;
NOWAIT:                       N O W A I T;
NVL:                          N V L;
NULL:                         N U L L;
NULLS:                        N U L L S;
NUMBER:                       N U M B E R;
NUMERIC:                      N U M E R I C;
NVARCHAR2:                    N V A R C H A R '2';
MATERIALIZED:                 M A T E R I A L I Z E D;
OBJECT:                       O B J E C T;
OF:                           O F;
OFF:                          O F F;
OID:                          O I D;
OIDINDEX:                     O I D I N D E X;
OLD:                          O L D;
OLTP:                         O L T P;
ON:                           O N;
ONLY:                         O N L Y;
OPEN:                         O P E N;
OPTIMAL:                      O P T I M A L;
OPTION:                       O P T I O N;
OR:                           O R;
ORADATA:                      O R A D A T A;
ORDER:                        O R D E R;
ORDINALITY:                   O R D I N A L I T Y;
OSERROR:                      O S E R R O R;
OUT:                          O U T;
OUTER:                        O U T E R;
OVER:                         O V E R;
OVERFLOW:                     O V E R F L O W;
OVERRIDING:                   O V E R R I D I N G;
PACKAGE:                      P A C K A G E;
PARALLEL:                     P A R A L L E L;
PARALLEL_ENABLE:              P A R A L L E L '_' E N A B L E;
PARAMETERS:                   P A R A M E T E R S;
PARENT:                       P A R E N T;
PARTITION:                    P A R T I T I O N;
PASSING:                      P A S S I N G;
PATH:                         P A T H;
PCTFREE:                      P C T F R E E;
PCTINCREASE:                  P C T I N C R E A S E;
PCTTHRESHOLD:                 P C T T H R E S H O L D;
PCTUSED:                      P C T U S E D;
PCTVERSION:                   P C T V E R S I O N;
PERCENT_ROWTYPE:              '%' R O W T Y P E;
PERCENT_TYPE:                 '%' T Y P E;
PIPELINED:                    P I P E L I N E D;
PIVOT:                        P I V O T;
PLAN:                         P L A N;
PLS_INTEGER:                  P L S '_' I N T E G E R;
PARTITIONS:                   P A R T I T I O N S;
POSITION:                     P O S I T I O N;
POSITIVE:                     P O S I T I V E;
POSITIVEN:                    P O S I T I V E N;
PRAGMA:                       P R A G M A;
PREBUILT:                     P R E B U I L T;
PRECEDING:                    P R E C E D I N G;
PRECISION:                    P R E C I S I O N;
PRESENT:                      P R E S E N T;
PRESERVE:                     P R E S E R V E;
PRIMARY:                      P R I M A R Y;
PRIOR:                        P R I O R;
PROCEDURE:                    P R O C E D U R E;
PUBLIC:                       P U B L I C;
PURGE:                        P U R G E;
QUERY:                        Q U E R Y;
RAISE:                        R A I S E;
RANGE:                        R A N G E;
RAW:                          R A W;
READ:                         R E A D;
READS:                        R E A D S;
REAL:                         R E A L;
REBUILD:                      R E B U I L D;
RECORD:                       R E C O R D;
RECORDS_PER_BLOCK:            R E C O R D S '_' P E R '_' B L O C K;
RECYCLE:                      R E C Y C L E;
REDUCED:                      R E D U C E D;
REF:                          R E F;
REFERENCE:                    R E F E R E N C E;
REFERENCES:                   R E F E R E N C E S;
REFERENCING:                  R E F E R E N C I N G;
REFRESH:                      R E F R E S H;
REJECT:                       R E J E C T;
REKEY:                        R E K E Y;
RELATIONAL:                   R E L A T I O N A L;
RELIES_ON:                    R E L I E S '_' O N;
RELY:                         R E L Y;
RENAME:                       R E N A M E;
REPLACE:                      R E P L A C E;
RESPECT:                      R E S P E C T;
RESTRICT_REFERENCES:          R E S T R I C T '_' R E F E R E N C E S;
RESULT:                       R E S U L T;
RESULT_CACHE:                 R E S U L T '_' C A C H E;
RETENTION:                    R E T E N T I O N;
RETURN:                       R E T U R N;
RETURNING:                    R E T U R N I N G;
REUSE:                        R E U S E;
REVERSE:                      R E V E R S E;
REVOKE:                       R E V O K E;
REWRITE:                      R E W R I T E;
RIGHT:                        R I G H T;
ROLE:                         R O L E;
ROLLBACK:                     R O L L B A C K;
ROLLUP:                       R O L L U P;
ROW:                          R O W;
ROWDEPENDENCIES:              R O W D E P E N D E N C I E S;
ROWID:                        R O W I D;
ROWS:                         R O W S;
RULES:                        R U L E S;
SALT:                         S A L T;
SAMPLE:                       S A M P L E;
SAVE:                         S A V E;
SAVEPOINT:                    S A V E P O I N T;
SCHEMA:                       S C H E M A;
SCHEMACHECK:                  S C H E M A C H E C K;
SCN:                          S C N;
SCOPE:                        S C O P E;
SEARCH:                       S E A R C H;
SECOND:                       S E C O N D;
SECUREFILE:                   S E C U R E F I L E;
SEED:                         S E E D;
SEGMENT:                      S E G M E N T;
SELECT:                       S E L E C T;
SELF:                         S E L F;
SEQUENCE:                     S E Q U E N C E;
SEQUENTIAL:                   S E Q U E N T I A L;
SERIALIZABLE:                 S E R I A L I Z A B L E;
SERIALLY_REUSABLE:            S E R I A L L Y '_' R E U S A B L E;
SERVERERROR:                  S E R V E R E R R O R;
SESSIONTIMEZONE:              S E S S I O N T I M E Z O N E;
SET:                          S E T;
SETS:                         S E T S;
SETTINGS:                     S E T T I N G S;
SHARE:                        S H A R E;
SHOW:                         S H O W;
SHRINK:                       S H R I N K;
SHUTDOWN:                     S H U T D O W N;
SIBLINGS:                     S I B L I N G S;
SIGNTYPE:                     S I G N T Y P E;
SIMPLE_INTEGER:               S I M P L E '_' I N T E G E R;
SINGLE:                       S I N G L E;
SIZE:                         S I Z E;
SKIP_:                        S K I P;
SMALLINT:                     S M A L L I N T;
SNAPSHOT:                     S N A P S H O T;
SOME:                         S O M E;
SORT:                         S O R T;
SPACE_KEYWORD:                S P A C E;
SPECIFICATION:                S P E C I F I C A T I O N;
SQLDATA:                      S Q L D A T A;
SQLERROR:                     S Q L E R R O R;
STANDALONE:                   S T A N D A L O N E;
START:                        S T A R T;
STARTUP:                      S T A R T U P;
STATEMENT:                    S T A T E M E N T;
STATEMENT_ID:                 S T A T E M E N T '_' I D;
STATIC:                       S T A T I C;
STATISTICS:                   S T A T I S T I C S;
STORAGE:                      S T O R A G E;
STORE:                        S T O R E;
STRING:                       S T R I N G;
SUBMULTISET:                  S U B M U L T I S E T;
SUBPARTITION:                 S U B P A R T I T I O N;
SUBPARTITIONS:                S U B P A R T I T I O N S;
SUBSTITUTABLE:                S U B S T I T U T A B L E;
SUBSTRING:                    S U B S T R (I N G)?;
SUBTYPE:                      S U B T Y P E;
SUCCESS:                      S U C C E S S;
SUPPLEMENTAL:                 S U P P L E M E N T A L;
SUSPEND:                      S U S P E N D;
SYSTEM:                       S Y S T E M;
TABLE:                        T A B L E;
TABLES:                       T A B L E S;
TABLESPACE:                   T A B L E S P A C E;
TEMPLATE:                     T E M P L A T E;
TEMPORARY:                    T E M P;
THAN:                         T H A N;
THE:                          T H E;
THEN:                         T H E N;
TIME:                         T I M E;
TIMESTAMP:                    T I M E S T A M P;
TIMESTAMP_LTZ_UNCONSTRAINED:  T I M E S T A M P '_' L T Z '_' U N C O N S T R A I N E D;
TIMESTAMP_TZ_UNCONSTRAINED:   T I M E S T A M P '_' T Z '_' U N C O N S T R A I N E D;
TIMESTAMP_UNCONSTRAINED:      T I M E S T A M P '_' U N C O N S T R A I N E D;
TIMEZONE_ABBR:                T I M E Z O N E '_' A B B R;
TIMEZONE_HOUR:                T I M E Z O N E '_' H O U R;
TIMEZONE_MINUTE:              T I M E Z O N E '_' M I N U T E;
TIMEZONE_REGION:              T I M E Z O N E '_' R E G I O N;
TO:                           T O;
TO_CHAR:                      T O '_' C H A R;
TO_DATE:                      T O '_' D A T E;
TRAILING:                     T R A I L I N G;
TRANSACTION:                  T R A N S A C T I O N;
TRANSLATE:                    T R A N S L A T E;
TREAT:                        T R E A T;
TRIGGER:                      T R I G G E R;
TRIM:                         T R I M;
TRUE:                         T R U E;
TRUNCATE:                     T R U N C A T E;
TRUSTED:                      T R U S T E D;
TYPE:                         T Y P E;
UNBOUNDED:                    U N B O U N D E D;
UNDER:                        U N D E R;
UNION:                        U N I O N;
UNIQUE:                       U N I Q U E;
UNLIMITED:                    U N L I M I T E D;
UNPIVOT:                      U N P I V O T;
UNTIL:                        U N T I L;
UNUSABLE:                     U N U S A B L E;
UNUSED:                       U N U S E D;
UPDATE:                       U P D A T E;
UPDATED:                      U P D A T E D;
UPGRADE:                      U P G R A D E;
UPSERT:                       U P S E R T;
UROWID:                       U R O W I D;
USE:                          U S E;
USING:                        U S I N G;
VALIDATE:                     V A L I D A T E;
VALUE:                        V A L U E;
VALUES:                       V A L U E S;
VARCHAR:                      V A R C H A R;
VARCHAR2:                     V A R C H A R '2';
VARIABLE:                     V A R I A B L E;
VARRAY:                       V A R R A Y;
VARRAYS:                      V A R R A Y S;
VARYING:                      V A R Y I N G;
VERBOSE:                      V E R B O S E;
VERSION:                      V E R S I O N;
VERSIONS:                     V E R S I O N S;
VIEW:                         V I E W;
VIRTUAL:                      V I R T U A L;
VISIBLE:                      V I S I B L E;
WAIT:                         W A I T;
WARNING:                      W A R N I N G;
WELLFORMED:                   W E L L F O R M E D;
WHEN:                         W H E N;
WHENEVER:                     W H E N E V E R;
WHERE:                        W H E R E;
WHILE:                        W H I L E;
WITH:                         W I T H;
WITHOUT:                      W I T H O U T;
WITHIN:                       W I T H I N;
WORK:                         W O R K;
WRITE:                        W R I T E;
XDB:                          X D B;
XML:                          X M L;
XMLAGG:                       X M L A G G;
XMLATTRIBUTES:                X M L A T T R I B U T E S;
XMLCAST:                      X M L C A S T;
XMLCOLATTVAL:                 X M L C O L A T T V A L;
XMLELEMENT:                   X M L E L E M E N T;
XMLEXISTS:                    X M L E X I S T S;
XMLFOREST:                    X M L F O R E S T;
XMLINDEX:                     X M L I N D E X;
XMLNAMESPACES:                X M L N A M E S P A C E S;
XMLPARSE:                     X M L P A R S E;
XMLPI:                        X M L P I;
XMLQUERY:                     X M L Q U E R Y;
XMLROOT:                      X M L R O O T;
XMLSCHEMA:                    X M L S C H E M A;
XMLSERIALIZE:                 X M L S E R I A L I Z E;
XMLTABLE:                     X M L T A B L E;
XMLTYPE:                      X M L T Y P E;
YEAR:                         Y E A R;
YES:                          Y E S;
YMINTERVAL_UNCONSTRAINED:     Y M I N T E R V A L '_' U N C O N S T R A I N E D;
ZONE:                         Z O N E;

PREDICTION:                   P R E D I C T I O N;
PREDICTION_BOUNDS:            P R E D I C T I O N '_' B O U N D S;
PREDICTION_COST:              P R E D I C T I O N '_' C O S T;
PREDICTION_DETAILS:           P R E D I C T I O N '_' D E T A I L S;
PREDICTION_PROBABILITY:       P R E D I C T I O N '_' P R O B A B I L I T Y;
PREDICTION_SET:               P R E D I C T I O N '_' S E T;

CUME_DIST:                    C U M E '_' D I S T;
DENSE_RANK:                   D E N S E '_' R A N K;
LISTAGG:                      L I S T A G G;
PERCENT_RANK:                 P E R C E N T '_' R A N K;
PERCENTILE_CONT:              P E R C E N T I L E '_' C O N T;
PERCENTILE_DISC:              P E R C E N T I L E '_' D I S C;
RANK:                         R A N K;

AVG:                          A V G;
CORR:                         C O R R;
LAG:                          L A G;
LEAD:                         L E A D;
MAX:                          M A X;
MEDIAN:                       M E D I A N;
MIN:                          M I N;
NTILE:                        N T I L E;
RATIO_TO_REPORT:              R A T I O '_' T O '_' R  E P O R T;
ROW_NUMBER:                   R O W '_' N U M B E R;
SUM:                          S U M;
VARIANCE:                     V A R I A N C E;
REGR_:                        R E G R '_';
STDDEV:                       S T D D E V;
VAR_:                         V A R '_';
COVAR_:                       C O V A R '_';

// Rule #358 <NATIONAL_CHAR_STRING_LIT> - subtoken typecast in <REGULAR_ID>, it also incorporates <character_representation>
//  Lowercase 'n' is a usual addition to the standard
NATIONAL_CHAR_STRING_LIT: N '\'' (~('\'' | '\r' | '\n' ) | '\'' '\'' | NEWLINE)* '\'';

//  Rule #040 <BIT_STRING_LIT> - subtoken typecast in <REGULAR_ID>
//  Lowercase 'b' is a usual addition to the standard
BIT_STRING_LIT: B ('\'' ('0' | '1')* '\'' /*SEPARATOR?*/ )+;

//  Rule #284 <HEX_STRING_LIT> - subtoken typecast in <REGULAR_ID>
//  Lowercase 'x' is a usual addition to the standard
HEX_STRING_LIT: X ('\'' ('a'..'f' | 'A'..'F' | '0'..'9')* '\'' /*SEPARATOR?*/ )+;
DOUBLE_PERIOD: '.' '.';
PERIOD:        '.';

//{ Rule #238 <EXACT_NUM_LIT>
//  This rule is a bit tricky - it resolves the ambiguity with <PERIOD>
//  It als44o incorporates <mantisa> and <exponent> for the <APPROXIMATE_NUM_LIT>
//  Rule #501 <signed_integer> was incorporated directly in the token <APPROXIMATE_NUM_LIT>
//  See also the rule #617 <unsigned_num_lit>
/*
    : (
            UNSIGNED_INTEGER
            ( '.' UNSIGNED_INTEGER
            | {$type = UNSIGNED_INTEGER;}
            ) ( E ('+' | '-')? UNSIGNED_INTEGER {$type = APPROXIMATE_NUM_LIT;} )?
    | '.' UNSIGNED_INTEGER ( E ('+' | '-')? UNSIGNED_INTEGER {$type = APPROXIMATE_NUM_LIT;} )?
    )
    (D | F)?
    ;*/

UNSIGNED_INTEGER: UNSIGNED_INTEGER_FRAGMENT;
APPROXIMATE_NUM_LIT: FLOAT_FRAGMENT (('e'|'E') ('+'|'-')? (FLOAT_FRAGMENT | UNSIGNED_INTEGER_FRAGMENT))? (D | F)?;

// Rule #--- <CHAR_STRING> is a base for Rule #065 <char_string_lit> , it incorporates <character_representation>
// and a superfluous subtoken typecasting of the "QUOTE"
CHAR_STRING: '\'' (~('\'' | '\r' | '\n') | '\'' '\'' | NEWLINE)* '\'';

// Perl-style quoted string, see Oracle SQL reference, chapter String Literals
CHAR_STRING_PERL    : Q ( QS_ANGLE | QS_BRACE | QS_BRACK | QS_PAREN) -> type(CHAR_STRING);
fragment QUOTE      : '\'' ;
fragment QS_ANGLE   : QUOTE '<' .*? '>' QUOTE ;
fragment QS_BRACE   : QUOTE '{' .*? '}' QUOTE ;
fragment QS_BRACK   : QUOTE '[' .*? ']' QUOTE ;
fragment QS_PAREN   : QUOTE '(' .*? ')' QUOTE ;
fragment QS_OTHER_CH: ~('<' | '{' | '[' | '(' | ' ' | '\t' | '\n' | '\r');

// Rule #163 <DELIMITED_ID>
DELIMITED_ID: '"' (~('"' | '\r' | '\n') | '"' '"')+ '"' ;

// Rule #546 <SQL_SPECIAL_CHAR> was split into single rules
PERCENT: '%';
AMPERSAND: '&';
LEFT_PAREN: '(';
RIGHT_PAREN: ')';
DOUBLE_ASTERISK: '**';
ASTERISK: '*';
PLUS_SIGN: '+';
MINUS_SIGN: '-';
COMMA: ',';
SOLIDUS: '/';
AT_SIGN: '@';
ASSIGN_OP: ':=';

// See OCI reference for more information about this
BINDVAR
    : ':' SIMPLE_LETTER  (SIMPLE_LETTER | '0' .. '9' | '_')*
    | ':' DELIMITED_ID  // not used in SQL but spotted in v$sqltext when using cursor_sharing
    | ':' UNSIGNED_INTEGER
    | QUESTION_MARK // not in SQL, not in Oracle, not in OCI, use this for JDBC
    ;

COLON: ':';
SEMICOLON: ';';
LESS_THAN_OR_EQUALS_OP: '<=';
LESS_THAN_OP: '<';
GREATER_THAN_OR_EQUALS_OP: '>=';
NOT_EQUAL_OP: '!='| '<>'| '^='| '~=';
CARRET_OPERATOR_PART: '^';
TILDE_OPERATOR_PART: '~';
EXCLAMATION_OPERATOR_PART: '!';
GREATER_THAN_OP: '>';

fragment
QUESTION_MARK: '?';

// protected UNDERSCORE : '_' SEPARATOR ; // subtoken typecast within <INTRODUCER>
CONCATENATION_OP: '||';
VERTICAL_BAR: '|';
EQUALS_OP: '=';

// Rule #532 <SQL_EMBDD_LANGUAGE_CHAR> was split into single rules:
LEFT_BRACKET: '[';
RIGHT_BRACKET: ']';

//{ Rule #319 <INTRODUCER>
INTRODUCER
    : '_' //(SEPARATOR {$type = UNDERSCORE;})?
    ;

//{ Rule #479 <SEPARATOR>
//  It was originally a protected rule set to be filtered out but the <COMMENT> and <'-'> clashed.
/*SEPARATOR
    : '-' -> type('-')
    | COMMENT -> channel(HIDDEN)
    | (SPACE | NEWLINE)+ -> channel(HIDDEN)
    ;*/
//}

SPACES: [ \t\r\n]+ -> skip;

//{ Rule #504 <SIMPLE_LETTER> - simple_latin _letter was generalised into SIMPLE_LETTER
//  Unicode is yet to be implemented - see NSF0
fragment
SIMPLE_LETTER
    : 'a'..'z'
    | 'A'..'Z'
    ;
//}

//  Rule #176 <DIGIT> was incorporated by <UNSIGNED_INTEGER>
//{ Rule #615 <UNSIGNED_INTEGER> - subtoken typecast in <EXACT_NUM_LIT>
fragment
UNSIGNED_INTEGER_FRAGMENT: ('0'..'9')+ ;

fragment
FLOAT_FRAGMENT
    : UNSIGNED_INTEGER* '.'? UNSIGNED_INTEGER+
    ;

//{ Rule #097 <COMMENT>
SINGLE_LINE_COMMENT: '--' ( ~('\r' | '\n') )* (NEWLINE|EOF) -> channel(HIDDEN);
MULTI_LINE_COMMENT: '/*' .*? '*/'                           -> channel(HIDDEN);

// SQL*Plus prompt
// TODO should be grammar rule, but tricky to implement
PROMPT
	: 'prompt' SPACE ( ~('\r' | '\n') )* (NEWLINE|EOF)
	;

//{ Rule #360 <NEWLINE>
fragment
NEWLINE: '\r'? '\n';

fragment
SPACE: [ \t];

//{ Rule #442 <REGULAR_ID> additionally encapsulates a few STRING_LITs.
//  Within testLiterals all reserved and non-reserved words are being resolved

// PLSQL keywords:

/*PLSQL_NON_RESERVED_COLUMNS: 'columns';
CLUSTERS: 'clusters';
COLAUTH: 'colauth';
COMPRESS: 'compress';
PLSQL_NON_RESERVED_CONNECT_BY_ROOT: 'connect_by_root';
CRASH: 'crash';
EXCLUSIVE: 'exclusive';
IDENTIFIED: 'identified';
INDEX: 'index';
INDEXES: 'indexes';
LOCK: 'lock';
MINUS: 'minus';
MODE: 'mode';
NOCOMPRESS: 'nocompress';
NOWAIT: 'nowait';
RESOURCE: 'resource';
SHARE: 'share';*/

// SQL92 keywords:

/*ALL: 'all';
ALTER: 'alter';
AND: 'and';

ANY: 'any';
AS: 'as';
ASC: 'asc';
BEGIN: 'begin';
BETWEEN: 'between';
BY: 'by';
CASE: 'case';
CHECK: 'check';
CONNECT: 'connect';
CREATE: 'create';
CURRENT: 'current';
CURSOR: 'cursor';
DATE: 'date';
DECLARE: 'declare';
DEFAULT: 'default';
DELETE: 'delete';
DESC: 'desc';
DISTINCT: 'distinct';
DROP: 'drop';
ELSE: 'else';
END: 'end';
//TODO "exception" is a keyword only withing the contex of the PL/SQL language
//while it can be an identifier(column name, table name) in SQL
//"exception" is a keyword if and only it is followed by "when"
EXCEPTION: 'exception';
EXISTS: 'exists';
FALSE: 'false';
FETCH: 'fetch';
FOR: 'for';
FROM: 'from';
GOTO: 'goto';
GRANT: 'grant';
GROUP: 'group';
HAVING: 'having';
IN: 'in';
INSERT: 'insert';
INTERSECT: 'intersect';
INTO: 'into';
IS: 'is';
LIKE: 'like';
NOT: 'not';
NULL: 'null';
OF: 'of';
ON: 'on';
OPTION: 'option';
OR: 'or';
ORDER: 'order';
OVERLAPS: 'overlaps';
PRIOR: 'prior';
PROCEDURE: 'procedure';
PUBLIC: 'public';
REVOKE: 'revoke';
SELECT: 'select';
SIZE: 'size';
START: 'start';
TABAUTH: 'tabauth';
TABLE: 'table';
THE: 'the';
THEN: 'then';
TO: 'to';
TRUE: 'true';
UNION: 'union';
UNIQUE: 'unique';
UPDATE: 'update';
VALUES: 'values';
VIEW: 'view';
VIEWS: 'views';
WHEN: 'when';
WHERE: 'where';
WITH: 'with';
USING: 'using';*/

REGULAR_ID: SIMPLE_LETTER (SIMPLE_LETTER | '$' | '_' | '#' | '0'..'9')*;
ZV: '@!' -> channel(HIDDEN);

fragment A: [aA];
fragment B: [bB];
fragment C: [cC];
fragment D: [dD];
fragment E: [eE];
fragment F: [fF];
fragment G: [gG];
fragment H: [hH];
fragment I: [iI];
fragment J: [jJ];
fragment K: [kK];
fragment L: [lL];
fragment M: [mM];
fragment N: [nN];
fragment O: [oO];
fragment P: [pP];
fragment Q: [qQ];
fragment R: [rR];
fragment S: [sS];
fragment T: [tT];
fragment U: [uU];
fragment V: [vV];
fragment W: [wW];
fragment X: [xX];
fragment Y: [yY];
fragment Z: [zZ];
