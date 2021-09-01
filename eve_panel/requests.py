
import param
from param.parameterized import String


class EveRequest(param.Parameterized):
    url = param.String()
    method = param.Selector(["GET", "POST", "OPTIONS", "PUT", "PATCH", "DELETE"])
    headers = param.Dict(constant=True)
    params = param.Dict(constant=True)
    content = param.ClassSelector((bytes, str))
    data = param.Dict()
    files = param.Dict()
    json = param.Dict()
    cookies = param.Dict()

    _timeout = param.Dict()

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        self._timeout = value
        
class EveGet(EveRequest):
    method = "GET"

class EvePost(EveRequest):
    method = "POST"

class EvePut(EveRequest):
    method = "PUT"

class EvePatch(EveRequest):
    method = "PATCH"

class EveDelete(EveRequest):
    method = "DELETE"


class EveRespone(param.Parameterized):
    request = param.ClassSelector(EveRequest)
    code = None
class EveErrorResponse(EveRespone):
    _status = param.String()
    _error = param.Dict()

class EvePostResponse(EveRespone):
    code = 201

class EveGetResponse(EveRespone):
    code = 200

class EvePutResponse(EveRespone):
    code = 200

class EvePatchResponse(EveRespone):
    code = 200

class EveDeleteResponse(EveRespone):
    code = 204


