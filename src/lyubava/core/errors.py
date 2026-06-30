class AppError(Exception):
    status_code = 500
    detail = "Application error."

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.detail)
        self.detail = detail or self.detail


class BadRequestError(AppError):
    status_code = 400
    detail = "Bad request."


class ServiceUnavailableError(AppError):
    status_code = 503
    detail = "Service is not available."


class UpstreamServiceError(AppError):
    status_code = 502
    detail = "Upstream request failed."
