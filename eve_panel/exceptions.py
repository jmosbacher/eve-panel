
class EvePanelError(Exception):
    pass

class AuthError(EvePanelError):
    pass

class ServerError(EvePanelError):
    def __init__(self, status_code, message=""):
        self.status_code = status_code
        super().__init__(message)
