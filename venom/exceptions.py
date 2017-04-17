from venom import Message
from venom.fields import Int32, String


# TODO consider moving that into the implementations. Should at least be moved into rpc.*
class ErrorResponse(Message):
    status = Int32()
    description = String()

    # TODO Repeat(String)
    path = String()

    # TODO helper for raising errors
    def raise_(self):
        if self.status == 501:
            raise NotImplemented_()
        # if self.status == 500:
        #         raise ServerError(self.message or '')
        #     if self.status == 404:
        #         raise NotFound(self.message or '')

        raise RuntimeError('HTTP status {}: {}'.format(self.status, self.description))


class Error(Exception):
    http_status = 500
    description = ''

    def __init__(self, message: str = None):
        if message:
            self.description = message

    def format(self) -> ErrorResponse:
        return ErrorResponse(status=self.http_status, description=self.description)


class NotImplemented_(Error):
    http_status = 501
    description = 'Not Implemented'


class NotFound(Error):
    http_status = 404
    description = 'Not Found'


class BadRequest(Error):
    http_status = 400
    description = 'Bad Request'


class Unauthorized(Error):
    http_status = 401
    description = 'Unauthorized'


class Forbidden(Error):
    http_status = 403
    description = 'Forbidden'


class Conflict(Error):
    http_status = 409
    description = 'Conflict'


class ServerError(Error):
    http_status = 500
    description = 'Internal Server Error'


class ValidationError(BadRequest):
    def __init__(self, message, path=None):
        super().__init__(message)
        self.path = path or []

    def format(self) -> ErrorResponse:
        msg = super().format()
        msg.description = self.description
        if self.path:
            msg.path = '.'.join(self.path)
        return msg
