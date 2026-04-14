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


class ArithmeticQuizGenerator(QuizGenerator):
    """Generates arithmetic quizzes for elementary school kids."""

    def generate(
        self,
        topic: str,
        count: int,
        word_weights: dict[str, int] | None = None,
    ) -> list[Question]:
        questions = []
        for _ in range(count):
            op = random.choice(["+", "-", "*", "/"])

            if op == "+":
                a = random.randint(0, 99)
                b = random.randint(0, 99 - a)
                answer = a + b
                question_text = f"{a} + {b}"
            elif op == "-":
                a = random.randint(0, 99)
                b = random.randint(0, 99)
                answer = a - b
                question_text = f"{a} - {b}"
            elif op == "*":
                a = random.randint(2, 15)
                b = random.randint(2, 99 // a)
                if random.choice([True, False]):
                    a, b = b, a
                answer = a * b
                question_text = f"{a} × {b}"
            else:  # op == "/"
                divisor = random.randint(2, 12)
                answer = random.randint(2, 12)
                dividend = (
                    divisor * answer
                )  # pick quotient first to guarantee whole-number result
                question_text = f"{dividend} ÷ {divisor}"

            options = self._generate_options(str(answer))
            questions.append(
                Question(word=question_text, translation=str(answer), options=options)
            )
        return questions

    def _generate_options(self, correct_answer: str) -> list[str]:
        """Helper to generate random distractors for arithmetic questions."""
        correct_answer_int = int(correct_answer)
        options = {correct_answer_int}
        while len(options) < 4:
            # Generate distractors close to the correct answer
            offset = random.randint(-5, 5)
            if offset == 0:
                continue
            distractor = correct_answer_int + offset
            options.add(distractor)

        str_options = [str(opt) for opt in options]
        random.shuffle(str_options)
        return str_options


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
                incorrect.append(f"Option {len(incorrect)+1}")
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
        if mode == "arithmetic":
            return ArithmeticQuizGenerator()
        elif mode == "standard":
            if not vocab_manager:
                raise ValueError("VocabularyManager is required for standard mode")
            return RandomQuizGenerator(vocab_manager)
        else:
            # Fallback for any other mode will be standard
            if not vocab_manager:
                raise ValueError("VocabularyManager is required for standard mode")
            return RandomQuizGenerator(vocab_manager)
