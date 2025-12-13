import random
from abc import ABC, abstractmethod
from typing import Dict, List
from .models import Question
from .vocabulary import VocabularyManager


# --- Strategy Pattern: Quiz Generators ---
class QuizGenerator(ABC):
    """Abstract Base Class for different quiz generation strategies."""

    def __init__(self, vocab_manager: VocabularyManager):
        self.vocab_manager = vocab_manager

    @abstractmethod
    def generate(self, topic: str, count: int) -> List[Question]:
        pass

    def _generate_options(
        self, correct_translation: str, all_words: List[Dict[str, str]]
    ) -> List[str]:
        """Helper to generate random distractors."""
        all_translations = {w["translation"] for w in all_words}
        all_translations.discard(correct_translation)

        num_options = 3
        if len(all_translations) < num_options:
            incorrect = list(all_translations)
            while len(incorrect) < num_options:
                incorrect.append(f"Option {len(incorrect)+1}")
        else:
            incorrect = random.sample(list(all_translations), num_options)

        options = [correct_translation] + incorrect
        random.shuffle(options)
        return options


class RandomQuizGenerator(QuizGenerator):
    """Standard mode: Randomly selects N words from the topic."""

    def generate(self, topic: str, count: int) -> List[Question]:
        word_list = self.vocab_manager.get_words(topic)
        if not word_list:
            return []

        selected_words = random.sample(word_list, min(count, len(word_list)))

        return [
            Question(
                word=item["word"],
                translation=item["translation"],
                options=self._generate_options(item["translation"], word_list),
            )
            for item in selected_words
        ]


class QuizFactory:
    """Factory to select the appropriate generator."""

    @staticmethod
    def create(mode: str, vocab_manager: VocabularyManager) -> QuizGenerator:
        # In the future, you can add "review", "hard", "ai_generated" modes here
        if mode == "standard":
            return RandomQuizGenerator(vocab_manager)
        else:
            # Fallback
            return RandomQuizGenerator(vocab_manager)
