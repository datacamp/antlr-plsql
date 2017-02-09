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
