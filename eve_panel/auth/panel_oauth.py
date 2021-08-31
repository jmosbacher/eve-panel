from .bearer import EveBearerAuth

class EvePanelAuth(EveBearerAuth):
    def login(self):
        import panel as pn
        self.token = pn.state.access_token or ""
        return bool(self.token)

