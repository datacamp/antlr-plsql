from sqlwhat.test_exercise import test_exercise as te
import pytest

def test_pass():
    result = {'id': [1], 'name': ['greg']}
    sct_payload = te(
        sct = "Ex().check_result()",
        student_code = "SELECT * FROM company",
        solution_code = "SELECT * FROM company",
        pre_exercise_code = "",
        student_conn = None,
        solution_conn = None,
        student_result = result,
        solution_result = result,
        ex_type="NormalExercise",
        error=[]
        )

    assert sct_payload.get('correct') is True

def test_fail():
    sol_result = {'id': [1], 'name': ['greg']}
    stu_result = {'id': [1, 2], 'name': ['greg', 'fred']}
    sct_payload = te(
        sct = "Ex().check_result()",
        student_code = "SELECT * FROM company",
        solution_code = "SELECT * FROM company",
        pre_exercise_code = "",
        student_conn = None,
        solution_conn = None,
        student_result = stu_result,
        solution_result = sol_result,
        ex_type="NormalExercise",
        error=[]
        )

    assert sct_payload.get('correct') is False

xfail_def = pytest.mark.xfail(reason="implement deferrel")

@pytest.mark.parametrize('sct', [
    "Ex().check_statement('select')",
    "Ex().check_statement('select').check_clause('target_list')",
    "Ex().test_student_typed('SELECT')",
    "Ex().has_equal_ast()",
    xfail_def("Ex().multi(test_student_typed('SELECT'))"),
    xfail_def("Ex().test_or(test_student_typed('SELECT'))"),
    xfail_def("Ex().test_correct(test_student_typed('SELECT'))"),
    "Ex().check_result()",
    "Ex().test_has_columns()",
    "Ex().test_nrows()",
    "Ex().test_ncols()",
    "Ex().test_column('id')"
    ])
def test_test_exercise_pass(sct):
    result = {'id': [1], 'name': ['greg']}
    sct_payload = te(
        sct = sct,
        student_code = "SELECT * FROM company",
        solution_code = "SELECT * FROM company",
        pre_exercise_code = "",
        student_conn = None,
        solution_conn = None,
        student_result =  result,
        solution_result = result,
        ex_type="NormalExercise",
        error=[]
        )

    assert sct_payload.get('correct') is True

@pytest.mark.parametrize('sct', [
    "Ex().check_statement('select').check_clause('target_list').has_equal_ast()",
    "Ex().test_student_typed('id', fixed=True)",
    "Ex().has_equal_ast()",
    xfail_def("Ex().multi(test_student_typed('id'))"),
    xfail_def("Ex().test_or(test_student_typed('id'))"),
    xfail_def("Ex().test_correct(test_student_typed('id'))"),
    "Ex().check_result()",
    "Ex().test_nrows()",
    "Ex().test_ncols()",
    "Ex().test_column('id')"
    ])
def test_test_exercise_fail(sct):
    sol_result = {'id': [1], 'name': ['greg']}
    stu_result = {'id2': [1, 2], 'name2': ['greg', 'fred'], 'c': [1,2]}
    sct_payload = te(
        sct = sct,
        student_code = "SELECT * FROM company",
        solution_code = "SELECT id FROM company",
        pre_exercise_code = "",
        student_conn = None,
        solution_conn = None,
        student_result = stu_result,
        solution_result = sol_result,
        ex_type="NormalExercise",
        error=[]
        )

    assert sct_payload.get('correct') is False

