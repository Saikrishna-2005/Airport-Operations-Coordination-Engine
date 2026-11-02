from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

from pydantic import model_validator


class SignupRequest(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=100
    )

    password: str = Field(
        min_length=8,
        max_length=128
    )

    confirm_password: str = Field(
        min_length=8,
        max_length=128
    )

    @model_validator(mode="after")
    def validate_signup(self):

        self.username = self.username.strip()

        if len(self.username) < 3:
            raise ValueError(
                "Username must contain at least 3 characters"
            )

        if self.password != self.confirm_password:
            raise ValueError(
                "Passwords do not match"
            )

        return self