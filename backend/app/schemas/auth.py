from pydantic import BaseModel, EmailStr, Field


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetVerify(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")


class PasswordResetConfirm(PasswordResetVerify):
    password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str
