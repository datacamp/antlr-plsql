import helper
import pytest
import os

db_path = os.path.join(os.path.dirname(__file__), 'create_sqlite_db.py')

@pytest.fixture
def dc_pec():
    return open(db_path).read()

@pytest.mark.backend
def test_pass(dc_pec):
    sct_payload = helper.run({
        'DC_PEC': dc_pec, 
        'DC_SOLUTION': "SELECT * FROM company",
        'DC_CODE': "SELECT * FROM company",
        'DC_SCT': "Ex().check_result()"
        })

    assert sct_payload.get('correct') is True

@pytest.mark.backend
@pytest.mark.parametrize('stu_query', [
    "SELECT id FROM company",
    "SELECT * FROM company WHERE id > 1"
    ])
def test_check_result_fail(dc_pec, stu_query):
    sct_payload = helper.run({
        'DC_PEC': dc_pec, 
        'DC_SOLUTION': "SELECT * FROM company",
        'DC_CODE': stu_query, 
        'DC_SCT': "Ex().check_result()"
        })

    assert sct_payload.get('correct') is False

@pytest.mark.backend
def test_ex_check_clause_pass(dc_pec):
    sct_payload = helper.run({
        'DC_PEC': dc_pec, 
        'DC_SOLUTION': "SELECT * FROM company WHERE id > 1",
        'DC_CODE': "SELECT id, NAME as name FROM company WHERE id = 3",  # note where exists, even if different
        'DC_SCT': "Ex().check_statement('select', 0).check_clause('where_clause')"
        })

    assert sct_payload.get('correct') is True

@pytest.mark.backend
def test_ex_check_clause_pass(dc_pec):
    sct_payload = helper.run({
        'DC_PEC': dc_pec, 
        'DC_SOLUTION': "SELECT * FROM company WHERE id > 1",
        'DC_CODE': "SELECT id, NAME as name FROM company2",
        'DC_SCT': "Ex().check_statement('select', 0).check_clause('where_clause')"
        })

    assert sct_payload.get('correct') is False

@pytest.mark.backend
def test_ex_check_clause_has_equal_ast_fail(dc_pec):
    sct_payload = helper.run({
        'DC_PEC': dc_pec, 
        'DC_SOLUTION': "SELECT * FROM company WHERE id > 1",
        'DC_CODE': "SELECT id, NAME as name FROM company2 WHERE id = 3",
        'DC_SCT': "Ex().check_statement('select', 0).check_clause('where_clause').has_equal_ast()"
        })

    assert sct_payload.get('correct') is False
