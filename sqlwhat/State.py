class State:
    def __init__(self,
                 student_code,
                 solution_code,
                 pre_exercise_code,
                 student_process,
                 solution_process,
                 raw_student_output,
                 reporter):

        for k,v in locals().items():
            if k != 'self': setattr(self, k, v)

        # TODO get connection and last result
        self.student_result  = student_process.getLastQueryResult()
        self.solution_result = solution_process.getLastQueryResult()
                 

