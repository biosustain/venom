from venom import Message
from venom.fields import Int32, String


# TODO consider moving that into the implementations. Should at least be moved into rpc.*
class ErrorResponse(Message):
    status = Int32()
    message = String()

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

        raise RuntimeError('HTTP status {}: {}'.format(self.status, self.message))



class Error(Exception):
    http_status = 500
    message = ''

    def format(self) -> ErrorResponse:
        return ErrorResponse(status=self.http_status, message=self.message)


class NotImplemented_(Error):
    http_status = 501
    message = 'Not Implemented'


class NotFound(Error):
    http_status = 404
    message = 'Not Found'


class BadRequest(Error):
    http_status = 400
    message = 'Bad Request'


class ServerError(Error):
    http_status = 500
    message = 'Internal Server Error'


class ValidationError(BadRequest):
    def __init__(self, message, path=None):
        self.message = message
        self.path = path or []

    def format(self) -> ErrorResponse:
        msg = super().format()
        msg.message = self.message
        if self.path:
           msg.path = '.'.join(self.path)
        return msg
