
def get_sct_payload(output):
    output = [out for out in output if out['type'] == 'sct']
    if (len(output) > 0):
        return(output[0]['payload'])
    else:
        print(output)
        return(None)

def run(data):
    from sqlbackend.Exercise import Exercise
    exercise = Exercise(data)
    output = exercise.runInit()
    if 'backend-error' in str(output):
        print(output)
        raise(ValueError("Backend error"))
    output = exercise.runSubmit(data)
    return(get_sct_payload(output))
