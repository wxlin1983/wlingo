import random
from abc import ABC, abstractmethod
from .models import Question, Word
from .vocabulary import VocabularyManager


# --- Strategy Pattern: Quiz Generators ---
class QuizGenerator(ABC):
    """Abstract Base Class for different quiz generation strategies."""

    @abstractmethod
    def generate(
        self,
        topic: str,
        count: int,
        word_weights: dict[str, int] | None = None,
    ) -> list[Question]:
        pass


class RandomQuizGenerator(QuizGenerator):
    """Standard mode: Randomly selects N words from the topic."""

    def __init__(self, vocab_manager: VocabularyManager):
        self.vocab_manager = vocab_manager

    def generate(
        self,
        topic: str,
        count: int,
        word_weights: dict[str, int] | None = None,
    ) -> list[Question]:
        word_list = self.vocab_manager.get_words(topic)
        if not word_list:
            return []

        count = min(count, len(word_list))
        if word_weights:
            selected_words = self._weighted_sample(word_list, word_weights, count)
        else:
            selected_words = random.sample(word_list, count)

        return [
            Question(
                word=item["word"],
                translation=item["translation"],
                options=self._generate_options(item["translation"], word_list),
            )
            for item in selected_words
        ]

    def _weighted_sample(
        self,
        word_list: list[Word],
        word_weights: dict[str, int],
        k: int,
    ) -> list[Word]:
        """Weighted sampling without replacement. Wrong-answer words get a boost."""
        pool = list(word_list)
        weights = [
            1 + min(word_weights.get(item["word"], 0), 3) for item in pool
        ]  # cap boost at 3 to prevent a single word from dominating
        selected = []
        for _ in range(k):
            total = sum(weights)
            r = random.uniform(0, total)
            cumulative = 0.0
            for i, w in enumerate(weights):
                cumulative += w
                if r < cumulative:
                    selected.append(pool[i])
                    pool.pop(i)
                    weights.pop(i)
                    break
        return selected

    def _generate_options(
        self, correct_translation: str, all_words: list[Word]
    ) -> list[str]:
        """Helper to generate random distractors."""
        all_translations = {w["translation"] for w in all_words}
        all_translations.discard(correct_translation)

        num_options = 3
        if len(all_translations) < num_options:
            incorrect = list(all_translations)
            while len(incorrect) < num_options:
                incorrect.append(f"Option {len(incorrect) + 1}")
        else:
            incorrect = random.sample(list(all_translations), num_options)

        options = [correct_translation] + incorrect
        random.shuffle(options)
        return options


class QuizFactory:
    """Factory to select the appropriate generator."""

    @staticmethod
    def create(
        mode: str, vocab_manager: VocabularyManager | None = None
    ) -> QuizGenerator:
        if not vocab_manager:
            raise ValueError("VocabularyManager is required for standard mode")
        if mode != "standard":
            raise ValueError(f"Unknown quiz mode: {mode!r}")
        return RandomQuizGenerator(vocab_manager)
