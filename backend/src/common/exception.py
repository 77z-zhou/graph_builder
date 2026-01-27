

class GraphBuilderException(Exception):
    """ 构建知识图谱的异常 """
    def __init__(self, message):
        self.message = message
        super().__init__(message)