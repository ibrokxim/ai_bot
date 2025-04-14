from pydantic import BaseModel

class UserContact(BaseModel):
    user_id: int
    phone_number: str 