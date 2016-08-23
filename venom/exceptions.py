

class Error(Exception):
    http_status = 500


class NotFound(Error):
    http_status = 404


class BadRequest(Error):
    http_status = 400


class ServerError(Error):
    http_status = 500


class ValidationError(BadRequest):

    def __init__(self, message, path=None):
        pass
