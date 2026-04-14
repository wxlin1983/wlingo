import logging
import os
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import settings
from .router import router


# --- Logging Setup ---
def setup_logging() -> None:
    logger = logging.getLogger("wlingo")
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)

    os.makedirs(settings.LOG_DIR, exist_ok=True)
    log_path = os.path.join(settings.LOG_DIR, settings.LOG_FILE)
    file_handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)
    # Also configure root logger to see logs from other libraries
    logging.basicConfig(level=logging.INFO)


# --- App Factory ---
def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
        root_path=settings.ROOT_PATH,
    )

    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

    app.include_router(router)

    return app
