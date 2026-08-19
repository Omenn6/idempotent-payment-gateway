from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Annotated, Union

from pydantic import BaseModel, Field, field_serializer, ConfigDict, PlainSerializer, StringConstraints
from pydantic.alias_generators import to_camel

from src.statuses import OperationStatus


PostgresUtcDT = Annotated[
    Union[datetime, str],
    PlainSerializer(
        lambda v: (
            v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if isinstance(v, datetime)
            else v.split(".")[0].replace(" ", "T").replace("+00:00", "").replace("+00", "") + "Z"
        ),
        return_type=str
    )
]


class BaseApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class OperationCreateRequest(BaseApiModel):
    operation_id: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
    amount: Decimal = Field(max_digits=12, decimal_places=2, gt=0)
    currency: Literal["RUB"]
    description: str | None = None


class OperationResponse(BaseApiModel):
    operation_id: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
    amount: Decimal = Field(max_digits=12, decimal_places=2, gt=0)
    currency: Literal["RUB"]
    description: str | None = None
    status: OperationStatus
    provider_payment_id: str | None = None

    @field_serializer("amount")
    def serialize_amount_to_str(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OperationEventResponse(BaseApiModel):
    event_id: int = Field(ge=1)
    type: OperationStatus
    from_status: OperationStatus | None = None
    to_status: OperationStatus
    message: str
    occurred_at: PostgresUtcDT


class ReceiptCallbackRequest(BaseApiModel):
    provider_payment_id: str = Field(min_length=1)
    operation_id: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
    result: Literal[OperationStatus.COMPLETED, OperationStatus.REJECTED]
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
