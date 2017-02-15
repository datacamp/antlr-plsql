import helper
import pytest
import os

db_path = os.path.join(os.path.dirname(__file__), 'create_sqlite_db.py')

@pytest.mark.backend
def test_pass():
    sct_payload = helper.run({
        'DC_PEC': open(db_path).read(),
        'DC_SOLUTION': "SELECT * FROM company",
        'DC_CODE': "SELECT * FROM company",
        'DC_SCT': "Ex().check_result()"
        })

    assert sct_payload.get('correct') is True

@pytest.mark.backend
def test_fail():
    sct_payload = helper.run({
        'DC_PEC': open(db_path).read(),
        'DC_SOLUTION': "SELECT * FROM company",
        'DC_CODE': "SELECT id, NAME as name FROM company",
        'DC_SCT': "Ex().check_result()"
        })

    assert sct_payload.get('correct') is False

@pytest.mark.backend
def test_ex_check_clause_pass():
    sct_payload = helper.run({
        'DC_PEC': open(db_path).read(),
        'DC_SOLUTION': "SELECT * FROM company WHERE id > 1",
        'DC_CODE': "SELECT id, NAME as name FROM company WHERE id = 3",  # note where exists, even if different
        'DC_SCT': "Ex().check_statement('select', 0).check_clause('where_clause')"
        })

    assert sct_payload.get('correct') is True

@pytest.mark.backend
def test_ex_check_clause_pass():
    sct_payload = helper.run({
        'DC_PEC': open(db_path).read(),
        'DC_SOLUTION': "SELECT * FROM company WHERE id > 1",
        'DC_CODE': "SELECT id, NAME as name FROM company2",
        'DC_SCT': "Ex().check_statement('select', 0).check_clause('where_clause')"
        })

    assert sct_payload.get('correct') is False

@pytest.mark.backend
def test_ex_check_clause_has_equal_ast_fail():
    sct_payload = helper.run({
        'DC_PEC': open(db_path).read(),
        'DC_SOLUTION': "SELECT * FROM company WHERE id > 1",
        'DC_CODE': "SELECT id, NAME as name FROM company2 WHERE id = 3",
        'DC_SCT': "Ex().check_statement('select', 0).check_clause('where_clause').has_equal_ast()"
        })

    assert sct_payload.get('correct') is False
