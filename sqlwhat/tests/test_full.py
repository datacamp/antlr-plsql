import helper
import pytest

def test_pass():
    sct_payload = helper.run({
        'DC_PEC': open('create_sqlite_db.py').read(),
        'DC_SOLUTION': "SELECT * FROM company",
        'DC_CODE': "SELECT * FROM company",
        'DC_SCT': "Ex().check_result()"
        })

    assert sct_payload.get('correct') is True

def test_fail():
    sct_payload = helper.run({
        'DC_PEC': open('create_sqlite_db.py').read(),
        'DC_SOLUTION': "SELECT * FROM company",
        'DC_CODE': "SELECT id, NAME as name FROM company",
        'DC_SCT': "Ex().check_result()"
        })

    assert sct_payload.get('correct') is False
