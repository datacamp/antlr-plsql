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
    
    # assumes that columns cannot be jagged in size
    n_stu = len(next(iter(state.student_result.values())))
    n_sol = len(next(iter(state.solution_result.values())))

    if n_stu != n_sol:
        _msg = msg.format(n_stu, n_sol)
        state.reporter.do_test(Test(_msg))

def test_ncols(state, msg="Result has {} column(s) but expected {}."):
    stu_res = state.student_result
    sol_res = state.solution_result
    
    n_stu = len(state.student_result)
    n_sol = len(state.solution_result)

    if n_stu != n_sol:
        _msg = msg.format(n_stu, n_sol)
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
