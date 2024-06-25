class ResponseMalformedException(BaseException):
    pass

class ConfigFileMalformed(BaseException):
    pass

class NoResponseException(BaseException):
    pass

class CantConnectToZodiac(BaseException):
    pass

class FatalError(BaseException):
    pass