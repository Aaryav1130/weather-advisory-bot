"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration for the Weather Advisory Bot."""

    # Groq LLM settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

    # Open-Meteo API endpoints (free, no key required)
    WEATHER_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    GEOCODING_API_URL: str = "https://geocoding-api.open-meteo.com/v1/search"

    # Weather fields to request from Open-Meteo
    CURRENT_WEATHER_FIELDS: list[str] = [
        "temperature_2m",
        "relative_humidity_2m",
        "apparent_temperature",
        "precipitation",
        "rain",
        "weather_code",
        "wind_speed_10m",
        "wind_gusts_10m",
        "uv_index",
    ]

    HOURLY_WEATHER_FIELDS: list[str] = [
        "temperature_2m",
        "precipitation_probability",
        "precipitation",
        "wind_speed_10m",
        "uv_index",
    ]

    # App settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    @classmethod
    def validate(cls) -> None:
        """Validate that required settings are present."""
        if not cls.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is required. Get a free key at https://console.groq.com"
            )


settings = Settings()
