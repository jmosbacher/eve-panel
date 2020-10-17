from .eve_model import EveModelBase


class Directory(EveModelBase):

    def __getattr__(self, key):
        pass
