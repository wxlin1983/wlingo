import pytest
from wlingo.quiz import RandomQuizGenerator, QuizFactory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_WORDS = [{"word": f"word{i}", "translation": f"trans{i}"} for i in range(20)]


class MockVocabManager:
    def get_words(self, topic: str):
        return SAMPLE_WORDS if topic == "test" else []


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

    def test_weighted_generate_no_duplicates(self):
        weights = {"word0": 3, "word1": 3, "word2": 3}
        questions = self.gen.generate("test", 10, word_weights=weights)
        words = [q.word for q in questions]
        assert len(words) == len(set(words))

    def test_weighted_generate_correct_count(self):
        weights = {"word0": 3}
        questions = self.gen.generate("test", 10, word_weights=weights)
        assert len(questions) == 10

    def test_weighted_generate_prefers_boosted_words(self):
        """A maximally boosted word should appear significantly more often than chance."""
        target = SAMPLE_WORDS[0]["word"]
        weights = {target: 3}  # weight = 1 + min(3,3) = 4x vs 1x for others

        # With 20 words, pick 5: uniform P(target) = 5/20 = 25%
        # Boosted: target weight=4 vs 1 for others → clearly higher probability
        appearances = sum(
            1
            for _ in range(200)
            if any(
                q.word == target
                for q in self.gen.generate("test", 5, word_weights=weights)
            )
        )
        # Conservatively expect well above 25% = 50/200
        assert appearances > 70

    def test_weighted_sample_returns_correct_count(self):
        weights = {"word0": 2, "word1": 1}
        result = self.gen._weighted_sample(SAMPLE_WORDS, weights, 5)
        assert len(result) == 5

    def test_weighted_sample_no_duplicates(self):
        weights = {"word0": 3}
        result = self.gen._weighted_sample(SAMPLE_WORDS, weights, 10)
        words = [r["word"] for r in result]
        assert len(words) == len(set(words))


# ---------------------------------------------------------------------------
# QuizFactory
# ---------------------------------------------------------------------------


class TestQuizFactory:
    def test_creates_random_generator(self):
        gen = QuizFactory.create("standard", MockVocabManager())
        assert isinstance(gen, RandomQuizGenerator)

    def test_without_vocab_manager_raises(self):
        with pytest.raises(ValueError):
            QuizFactory.create("standard")
