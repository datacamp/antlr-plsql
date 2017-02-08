class State:
    def __init__(self,
                 student_code,
                 solution_code,
                 pre_exercise_code,
                 student_conn,
                 solution_conn,
                 student_result,
                 solution_result,
                 reporter):

        for k,v in locals().items():
            if k != 'self': setattr(self, k, v)
