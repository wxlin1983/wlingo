import pytest
from wlingo.quiz import ArithmeticQuizGenerator, RandomQuizGenerator, QuizFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_WORDS = [{"word": f"word{i}", "translation": f"trans{i}"} for i in range(20)]


class MockVocabManager:
    def get_words(self, topic: str):
        return SAMPLE_WORDS if topic == "test" else []


# ---------------------------------------------------------------------------
# ArithmeticQuizGenerator
# ---------------------------------------------------------------------------


class TestArithmeticQuizGenerator:
    def setup_method(self):
        self.gen = ArithmeticQuizGenerator()

    def test_generates_requested_count(self):
        assert len(self.gen.generate("arithmetic", 10)) == 10

    def test_each_question_has_four_options(self):
        for q in self.gen.generate("arithmetic", 20):
            assert len(q.options) == 4, f"Expected 4 options, got {q.options}"

    def test_correct_answer_always_in_options(self):
        for q in self.gen.generate("arithmetic", 50):
            assert q.translation in q.options

    def test_all_options_are_unique(self):
        for q in self.gen.generate("arithmetic", 20):
            assert len(set(q.options)) == 4

    def test_division_always_produces_integer_result(self):
        """÷ questions should never have decimal answers."""
        for q in self.gen.generate("arithmetic", 200):
            if "÷" in q.word:
                assert "." not in q.translation, (
                    f"Division question '{q.word}' has non-integer answer '{q.translation}'"
                )

    def test_generate_options_includes_correct_answer(self):
        options = self.gen._generate_options("42")
        assert "42" in options

    def test_generate_options_returns_four_entries(self):
        assert len(self.gen._generate_options("10")) == 4

    def test_generate_options_all_unique(self):
        opts = self.gen._generate_options("10")
        assert len(set(opts)) == 4


# ---------------------------------------------------------------------------
# RandomQuizGenerator
# ---------------------------------------------------------------------------


class TestRandomQuizGenerator:
    def setup_method(self):
        self.gen = RandomQuizGenerator(MockVocabManager())

    def test_generates_requested_count(self):
        assert len(self.gen.generate("test", 10)) == 10

    def test_correct_answer_in_options(self):
        for q in self.gen.generate("test", 10):
            assert q.translation in q.options

    def test_each_question_has_four_options(self):
        for q in self.gen.generate("test", 10):
            assert len(q.options) == 4

    def test_all_options_unique(self):
        for q in self.gen.generate("test", 10):
            assert len(set(q.options)) == 4

    def test_unknown_topic_returns_empty_list(self):
        assert self.gen.generate("nonexistent", 5) == []

    def test_count_capped_at_vocabulary_size(self):
        """If count > vocab size, returns at most len(vocab) questions."""

        class TinyVocab:
            def get_words(self, topic):
                return [
                    {"word": "a", "translation": "alpha"},
                    {"word": "b", "translation": "beta"},
                ]

        gen = RandomQuizGenerator(TinyVocab())
        assert len(gen.generate("test", 100)) == 2

    def test_options_padded_when_vocab_too_small(self):
        """With only 1 word, distractors are synthetic so we still get 4 options."""

        class SingleWordVocab:
            def get_words(self, topic):
                return [{"word": "hello", "translation": "你好"}]

        gen = RandomQuizGenerator(SingleWordVocab())
        questions = gen.generate("test", 1)
        assert len(questions[0].options) == 4

    def test_no_duplicate_questions_in_one_session(self):
        questions = self.gen.generate("test", 10)
        words = [q.word for q in questions]
        assert len(words) == len(set(words))


# ---------------------------------------------------------------------------
# QuizFactory
# ---------------------------------------------------------------------------


class TestQuizFactory:
    def test_arithmetic_mode_returns_arithmetic_generator(self):
        gen = QuizFactory.create("arithmetic")
        assert isinstance(gen, ArithmeticQuizGenerator)

    def test_standard_mode_returns_random_generator(self):
        gen = QuizFactory.create("standard", MockVocabManager())
        assert isinstance(gen, RandomQuizGenerator)

    def test_standard_without_vocab_manager_raises(self):
        with pytest.raises(ValueError):
            QuizFactory.create("standard")

    def test_unknown_mode_falls_back_to_random_generator(self):
        gen = QuizFactory.create("unknown_mode", MockVocabManager())
        assert isinstance(gen, RandomQuizGenerator)

    def test_unknown_mode_without_vocab_manager_raises(self):
        with pytest.raises(ValueError):
            QuizFactory.create("unknown_mode")
