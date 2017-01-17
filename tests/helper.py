class MockProcess:
    def __init__(self, result):
        self.result = result

    def getLastQueryResult(self):
        return self.result
    
    def getSqlConnection(self):
        pass
