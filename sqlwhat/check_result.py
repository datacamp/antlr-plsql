from pythonwhat.Test import TestFail, Test

def check_result(state, msg="Incorrect result."):
    stu_res = state.student_result
    sol_res = state.solution_result

    # empty test
    test_has_columns(state)
    # row test
    test_nrows(state)
    # column tests
    for k in sol_res:
        test_column(state, k)

    return state

def test_has_columns(state, msg="You result did not output any columns."):
    if not state.student_result:
        state.reporter.do_test(Test(msg))

def test_nrows(state, msg="Result has {} row(s) but expected {}."):

    stu_res = state.student_result
    sol_res = state.solution_result
    
    a_stu_col = next(iter(stu_res.values()))
    a_sol_col = next(iter(sol_res.values()))

    if len(a_stu_col) != len(a_sol_col):
        _msg = msg.format(len(a_stu_col), len(a_sol_col))
        state.reporter.do_test(Test(_msg))

def test_column(state, name, msg="Column {} does not match the solution", 
                match = ('exact', 'alias', 'any')[0],
                test = 'equivalent'):

    stu_res = state.student_result
    sol_res = state.solution_result

    src_col = sol_res[name]

    # get submission columns to test against
    if match == 'any':
        dst_cols = list(stu_res.values())
    elif match == 'alias':
        raise NotImplementedError()
    elif match == "exact":
        dst_cols = [stu_res.get(name)]
    else:
        raise BaseException("match must be one of 'any', 'alias', 'exact'")

    # test that relevant submission columns contain the solution column
    if src_col not in dst_cols:
        _msg = msg.format(name)
        state.reporter.do_test(Test(_msg))
