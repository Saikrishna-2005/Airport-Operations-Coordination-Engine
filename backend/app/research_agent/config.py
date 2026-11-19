from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')
    LLM_PROVIDER: Literal['gemini','ollama'] = 'gemini'
    GOOGLE_API_KEY: str = ''
    GEMINI_MODEL: str = 'gemini-3.5-flash-lite'
    OLLAMA_BASE_URL: str = 'http://localhost:11434'
    OLLAMA_MODEL: str = 'llama3'
    WEATHER_PROVIDER: str = 'open-meteo'
    FLIGHT_PROVIDER: str = 'opensky'
    FLIGHT_API_KEY: str = ''
    FLIGHT_CLIENT_ID: str = ''
    FLIGHT_CLIENT_SECRET: str = ''
    OPENSKY_STATES_CREDIT_BUDGET: int = Field(default=0, ge=0)
    OPENSKY_FLIGHTS_CREDIT_BUDGET: int = Field(default=0, ge=0)
    OPENSKY_TRACKS_CREDIT_BUDGET: int = Field(default=0, ge=0)
    OPENSKY_AUTH_BUDGET: int = Field(default=0, ge=0)
    OPENSKY_COOLDOWN_SECONDS: int = Field(default=300, ge=1)
    CIRIUM_ENABLED: bool = False
    CIRIUM_BASE_URL: str = ''
    CIRIUM_TOKEN_URL: str = ''
    CIRIUM_CLIENT_ID: str = ''
    CIRIUM_CLIENT_SECRET: str = ''
    CIRIUM_TIMEOUT_SECONDS: int = Field(default=30, ge=1)
    CIRIUM_CACHE_TTL_SECONDS: int = Field(default=300, ge=0)
    CIRIUM_REQUEST_BUDGET: int = Field(default=0, ge=0)
    CIRIUM_INITIAL_USED: int = Field(default=0, ge=0)
    CIRIUM_COOLDOWN_SECONDS: int = Field(default=300, ge=1)
    FLIGHT_INTEGRATION_ENABLED: bool = False
    FLIGHT_TRACKING_PROVIDER: str = 'opensky'
    FLIGHT_OPERATIONAL_PROVIDER: str = 'cirium'
    SYNTHETIC_FLIGHT_CACHE_ENABLED: bool = False
    SYNTHETIC_FLIGHT_CACHE_TTL_SECONDS: int = Field(default=15, ge=0, le=60)
    REQUEST_TIMEOUT_SECONDS: int = Field(default=30, ge=1)
    LOG_LEVEL: str = 'INFO'
    DATA_MODE: Literal['live','synthetic'] = 'synthetic'

settings = Settings()
