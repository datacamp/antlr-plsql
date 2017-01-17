from sqlwhat import check_funcs
from sqlwhat.State import State
from pythonwhat.Test import TestFail
from pythonwhat.Reporter import Reporter

def test_exercise(sct,
                  student_code,
                  solution_code,
                  pre_exercise_code,
                  student_process,
                  solution_process,
                  raw_student_output,
                  ex_type,
                  error):
    """
    """

    # TODO: put reporter on state
    state = State(
        student_code = student_code,
        solution_code = solution_code,
        pre_exercise_code = pre_exercise_code,
        student_process = student_process,
        solution_process = solution_process,
        raw_student_output = raw_student_output,
        reporter = Reporter())

    State.root_state = state

    try:
        exec(sct, check_funcs.__dict__)
    except TestFail: pass

    return(state.reporter.build_payload(error))
