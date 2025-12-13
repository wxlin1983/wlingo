class Settings:
    PROJECT_NAME: str = "wlingo"
    DEBUG: bool = False
    LOG_DIR: str = "log"
    LOG_FILE: str = "wlingo.log"
    VOCAB_DIR: str = "vocabulary"
    TEST_SIZE: int = 15
    SESSION_COOKIE_NAME: str = "quiz_session_id"
    SESSION_TIMEOUT_MINUTES: int = 120


settings = Settings()
