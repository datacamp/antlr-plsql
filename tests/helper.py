from pythonbackend.Exercise import SqlExercise

def get_sct_payload(output):
    output = [out for out in output if out['type'] == 'sct']
    if (len(output) > 0):
        return(output[0]['payload'])
    else:
        print(output)
        return(None)

def run(data):
    exercise = SqlExercise(data)
    output = exercise.runInit()
    if 'backend-error' in str(output):
        print(output)
        raise(ValueError("Backend error"))
    output = exercise.runSubmit(data)
    return(get_sct_payload(output))

class MockProcess:
    def __init__(self, result):
        self.result = result

    def getLastQueryResult(self):
        return self.result
    
    def getSqlConnection(self):
        pass
