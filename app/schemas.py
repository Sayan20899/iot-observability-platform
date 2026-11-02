from pydantic import BaseModel, ConfigDict, Field

class DeviceCreate(BaseModel):
    device_id: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=120)
    location: str = Field(default="Unknown", max_length=120)

class TelemetryCreate(BaseModel):
    device_id: str = Field(min_length=2, max_length=80)
    temperature: float = Field(ge=-50, le=150)
    humidity: float = Field(ge=0, le=100)
    power: float = Field(ge=0, le=100000)

class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    device_id: str
    name: str
    location: str
    status: str
