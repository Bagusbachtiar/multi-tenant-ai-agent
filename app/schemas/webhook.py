from pydantic import BaseModel, ConfigDict, Field


class WhatsAppIncoming(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_number: str = Field(alias="from")
    message: str


class WhatsAppReply(BaseModel):
    reply: str
    session_id: str
