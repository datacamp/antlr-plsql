def test_exercise(code, *args, **kwargs):

    if ('persons' in code.lower()):
        return({
            "correct": True,
            "message": "Great work!"
        })
    else:
        return({
            "correct": False,
            "message": "Wrong!!"
        })
