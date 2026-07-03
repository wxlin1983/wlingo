from .config import settings
from .vocabulary import VocabularyManager

vocab_manager: VocabularyManager = VocabularyManager(settings.VOCAB_DIR)
