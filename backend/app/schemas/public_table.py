from pydantic import BaseModel, ConfigDict


class PublicTableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    label: str
