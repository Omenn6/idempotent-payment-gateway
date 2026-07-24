from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_serializer


class OperationCreateRequest(BaseModel):
    operationId: str = Field(min_length=1)
    amount: Decimal = Field(max_digits=12, decimal_places=2, gt=0)
    currency: Literal["RUB"]
    description: str | None = None


class OperationResponse(BaseModel):
    operationId: str = Field(min_length=1)
    amount: Decimal = Field(max_digits=12, decimal_places=2, gt=0)
    currency: Literal["RUB"]
    description: str | None = None
    status: Literal["CREATED", "PROCESSING", "COMPLETED", "REJECTED"]
    providerPaymentId: str | None = None

    @field_serializer("amount")
    def serialize_amount_to_str(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OperationEventResponse(BaseModel):
    eventId: int = Field(ge=1)
    type: Literal["CREATED", "PROCESSING", "COMPLETED", "REJECTED"]
    fromStatus: Literal["CREATED", "PROCESSING", "COMPLETED", "REJECTED"] | None = None
    toStatus: Literal["CREATED", "PROCESSING", "COMPLETED", "REJECTED"]
    message: str = Field(min_length=1)
    occurredAt: datetime


class ReceiptCallbackRequest(BaseModel):
    providerPaymentId: str = Field(min_length=1)
    operationId: str = Field(min_length=1)
    result: Literal["COMPLETED", "REJECTED"]
    message: str = Field(min_length=1)
    occurredAt: datetime


class ProviderPaymentRequest(BaseModel):
    operationId: str = Field(min_length=1)
    amount: Decimal = Field(max_digits=12, decimal_places=2, gt=0)
    currency: Literal["RUB"]

    @field_serializer("amount")
    def serialize_amount_to_str(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ProviderPaymentResponse(BaseModel):
    providerPaymentId: str = Field(min_length=1)
    status: Literal["ACCEPTED"]
