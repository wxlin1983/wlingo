import os


class Settings:
    PROJECT_NAME: str = "wlingo"
    DEBUG: bool = False
    LOG_DIR: str = "log"
    LOG_FILE: str = "wlingo.log"
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    VOCAB_DIR: str = "vocabulary"
    STATIC_DIR: str = "static"
    TEST_SIZE: int = 15
    SESSION_COOKIE_NAME: str = "quiz_session_id"
    SESSION_TIMEOUT_MINUTES: int = 120
    USER_COOKIE_NAME: str = "wlingo_user_id"
    USER_STATS_TTL_DAYS: int = 90
    ROOT_PATH: str = os.environ.get("ROOT_PATH", "")
    ADMIN_TOKEN: str = os.environ.get("ADMIN_TOKEN", "")
    COOKIE_SECURE: bool = os.environ.get("COOKIE_SECURE", "false").lower() == "true"


settings = Settings()
