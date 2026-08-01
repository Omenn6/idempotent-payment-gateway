from fastapi import status, HTTPException


class PaymentGatewayException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Внутренняя ошибка платежного шлюза"

    def __init__(self, *args, **kwargs):
        super().__init__(self.detail, *args, **kwargs)


class OperationAlreadyExistsError(PaymentGatewayException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Операция с таким operationId уже существует"


class OperationNotFoundError(PaymentGatewayException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Операция с таким operationId не найдена"


class PaymentGatewayHTTPException(HTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Внутренняя ошибка платежного шлюза"

    def __init__(self):
        super().__init__(status_code=self.status_code, detail=self.detail)


class OperationAlreadyExistsHTTPException(PaymentGatewayHTTPException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Операция с таким operationId уже существует"


class OperationNotFoundHTTPException(PaymentGatewayHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Операция с таким operationId не найдена"
