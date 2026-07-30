from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, ConfigDict
from pydantic.alias_generators import to_camel


class BaseApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class OperationCreateRequest(BaseApiModel):
    operation_id: str = Field(min_length=1)
    amount: Decimal = Field(max_digits=12, decimal_places=2, gt=0)
    currency: Literal["RUB"]
    description: str | None = None


class OperationResponse(BaseApiModel):
    operation_id: str = Field(min_length=1)
    amount: Decimal = Field(max_digits=12, decimal_places=2, gt=0)
    currency: Literal["RUB"]
    description: str | None = None
    status: Literal["CREATED", "PROCESSING", "COMPLETED", "REJECTED"]
    provider_payment_id: str | None = None

    @field_serializer("amount")
    def serialize_amount_to_str(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OperationEventResponse(BaseApiModel):
    event_id: int = Field(ge=1)
    type: Literal["CREATED", "PROCESSING", "COMPLETED", "REJECTED"]
    from_status: Literal["CREATED", "PROCESSING", "COMPLETED", "REJECTED"] | None = None
    to_status: Literal["CREATED", "PROCESSING", "COMPLETED", "REJECTED"]
    message: str = Field(min_length=1)
    occurred_at: datetime


class ReceiptCallbackRequest(BaseApiModel):
    provider_payment_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    result: Literal["COMPLETED", "REJECTED"]
    message: str = Field(min_length=1)
    occurred_at: datetime


class ProviderPaymentRequest(BaseApiModel):
    operation_id: str = Field(min_length=1)
    amount: Decimal = Field(max_digits=12, decimal_places=2, gt=0)
    currency: Literal["RUB"]

    @field_serializer("amount")
    def serialize_amount_to_str(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ProviderPaymentResponse(BaseApiModel):
    provider_payment_id: str = Field(min_length=1)
    status: Literal["ACCEPTED"]
