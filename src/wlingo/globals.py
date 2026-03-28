from fastapi.templating import Jinja2Templates

from .config import settings
from .vocabulary import VocabularyManager

templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)
vocab_manager = VocabularyManager(settings.VOCAB_DIR)
