import param
import panel as pn
# from .eve_model import EveModelBase

class EveClientAuth(param.Parameterized):
    
    def get_headers(self):
        raise NotImplementedError

    def login(self):
        raise NotImplementedError

class EveBearerAuth(EveClientAuth):
    token = param.String()

    def get_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        else:
            return {}

    def login(self):
        return bool(self.token)

    def panel(self):
        return pn.panel(self.param.token)