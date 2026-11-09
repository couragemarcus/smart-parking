from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./parking.db"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    VISITOR_SESSION_EXPIRE_MINUTES: int = 120
    RESERVATION_TIMEOUT_MINUTES: int = 5
    DETECTION_THRESHOLD_CM: float = 50.0
    INSTITUTION_NAME: str = "Ho Technical University"
    PARKING_LAT: float = 6.5885794
    PARKING_LON: float = 0.4660595
    HARDWARE_MODE: bool = False
    GPIO_TRIGGER_PIN: int = 18
    GPIO_ECHO_PIN: int = 24
    BACKEND_URL: str = "http://localhost:8000"
    DEVICE_ID: str = "rpi-sensor-01"
    DEVICE_SECRET: str = "change-device-secret"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    NUM_SPACES: int = 4

    class Config:
        env_file = ".env"

settings = Settings()
