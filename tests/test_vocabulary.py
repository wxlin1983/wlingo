from wlingo.vocabulary import VocabularyManager

# ---------------------------------------------------------------------------
# Loading behaviour
# ---------------------------------------------------------------------------


def test_load_valid_csv(tmp_path):
    (tmp_path / "Fruits.csv").write_text(
        "word,translation\napple,苹果\nbanana,香蕉\n", encoding="utf-8"
    )
    vm = VocabularyManager(str(tmp_path))
    assert "Fruits" in vm.vocab_sets
    assert len(vm.vocab_sets["Fruits"]) == 2


def test_load_multiple_csvs(tmp_path):
    (tmp_path / "A.csv").write_text("word,translation\na,1\n")
    (tmp_path / "B.csv").write_text("word,translation\nb,2\n")
    vm = VocabularyManager(str(tmp_path))
    assert "A" in vm.vocab_sets and "B" in vm.vocab_sets


def test_csv_missing_columns_is_skipped(tmp_path):
    (tmp_path / "Bad.csv").write_text("term,meaning\nhello,你好\n")
    vm = VocabularyManager(str(tmp_path))
    assert "Bad" not in vm.vocab_sets


def test_malformed_csv_is_skipped(tmp_path):
    (tmp_path / "Broken.csv").write_bytes(b"\xff\xfe bad utf content")
    vm = VocabularyManager(str(tmp_path))
    assert "Broken" not in vm.vocab_sets


def test_empty_directory_loads_dummy_data(tmp_path):
    vm = VocabularyManager(str(tmp_path))
    assert "default_dummy" in vm.vocab_sets


def test_nonexistent_directory_is_created(tmp_path):
    new_dir = tmp_path / "new_subdir"
    vm = VocabularyManager(str(new_dir))
    # Directory is created, but load_all returns early — no words loaded yet.
    assert new_dir.exists()
    assert len(vm.vocab_sets) == 0


# ---------------------------------------------------------------------------
# Spelling subdirectory / quiz_type
# ---------------------------------------------------------------------------


def test_top_level_csv_is_multiple_choice(tmp_path):
    (tmp_path / "Fruits.csv").write_text("word,translation\napple,苹果\n")
    vm = VocabularyManager(str(tmp_path))
    assert vm.get_quiz_type("Fruits") == "multiple_choice"


def test_spelling_subdirectory_csv_is_spelling_type(tmp_path):
    spelling_dir = tmp_path / "spelling"
    spelling_dir.mkdir()
    (spelling_dir / "KanjiKana.csv").write_text("word,translation\n漢字,かんじ\n")
    vm = VocabularyManager(str(tmp_path))
    assert "KanjiKana" in vm.vocab_sets
    assert vm.get_quiz_type("KanjiKana") == "spelling"


def test_spelling_topic_appears_in_get_topics_with_quiz_type(tmp_path):
    spelling_dir = tmp_path / "spelling"
    spelling_dir.mkdir()
    (spelling_dir / "KanjiKana.csv").write_text("word,translation\n漢字,かんじ\n")
    vm = VocabularyManager(str(tmp_path))
    topic = next(t for t in vm.get_topics() if t["id"] == "KanjiKana")
    assert topic["quiz_type"] == "spelling"


def test_missing_spelling_subdirectory_is_silently_skipped(tmp_path):
    (tmp_path / "Fruits.csv").write_text("word,translation\napple,苹果\n")
    # No "spelling" subdirectory exists at all.
    vm = VocabularyManager(str(tmp_path))
    assert "Fruits" in vm.vocab_sets
    assert len(vm.vocab_sets) == 1


def test_get_quiz_type_unknown_topic_defaults_to_multiple_choice(tmp_path):
    vm = VocabularyManager(str(tmp_path))
    assert vm.get_quiz_type("DoesNotExist") == "multiple_choice"


# ---------------------------------------------------------------------------
# Romaji input detection
# ---------------------------------------------------------------------------


def test_kana_answers_enable_romaji_input(tmp_path):
    spelling_dir = tmp_path / "spelling"
    spelling_dir.mkdir()
    (spelling_dir / "KanjiKana.csv").write_text(
        "word,translation\n漢字,かんじ\n日本,にほん\n"
    )
    vm = VocabularyManager(str(tmp_path))
    assert vm.get_romaji_input("KanjiKana") is True


def test_latin_answers_do_not_enable_romaji_input(tmp_path):
    spelling_dir = tmp_path / "spelling"
    spelling_dir.mkdir()
    (spelling_dir / "ChineseSpelling.csv").write_text(
        "word,translation\n你好,hello\n世界,world\n"
    )
    vm = VocabularyManager(str(tmp_path))
    assert vm.get_romaji_input("ChineseSpelling") is False


def test_multiple_choice_topic_never_gets_romaji_input(tmp_path):
    # Even if a top-level (multiple-choice) topic happened to have kana
    # translations, romaji input is only ever computed for spelling topics.
    (tmp_path / "Kana.csv").write_text("word,translation\nhello,かんじ\n")
    vm = VocabularyManager(str(tmp_path))
    assert vm.get_quiz_type("Kana") == "multiple_choice"
    assert vm.get_romaji_input("Kana") is False


def test_get_romaji_input_unknown_topic_defaults_to_false(tmp_path):
    vm = VocabularyManager(str(tmp_path))
    assert vm.get_romaji_input("DoesNotExist") is False


# ---------------------------------------------------------------------------
# get_words
# ---------------------------------------------------------------------------


def test_get_words_returns_correct_records(tmp_path):
    (tmp_path / "Animals.csv").write_text(
        "word,translation\ncat,猫\ndog,狗\n", encoding="utf-8"
    )
    vm = VocabularyManager(str(tmp_path))
    words = vm.get_words("Animals")
    assert {"word": "cat", "translation": "猫", "explanation": ""} in words
    assert {"word": "dog", "translation": "狗", "explanation": ""} in words


def test_get_words_unknown_topic_returns_empty(tmp_path):
    vm = VocabularyManager(str(tmp_path))
    assert vm.get_words("DoesNotExist") == []


# ---------------------------------------------------------------------------
# get_topics
# ---------------------------------------------------------------------------


def test_get_topics_returns_sorted_list(tmp_path):
    (tmp_path / "Zebra.csv").write_text("word,translation\nz,z\n")
    (tmp_path / "Apple.csv").write_text("word,translation\na,a\n")
    vm = VocabularyManager(str(tmp_path))
    names = [t["name"] for t in vm.get_topics()]
    assert names == sorted(names)


def test_get_topics_correct_structure(tmp_path):
    (tmp_path / "Test.csv").write_text("word,translation\nhello,你好\nworld,世界\n")
    vm = VocabularyManager(str(tmp_path))
    topic = next(t for t in vm.get_topics() if t["id"] == "Test")
    assert topic["name"] == "Test"
    assert topic["count"] == 2


def test_get_topics_underscore_becomes_title_case(tmp_path):
    (tmp_path / "my_topic.csv").write_text("word,translation\na,b\n")
    vm = VocabularyManager(str(tmp_path))
    topic = next(t for t in vm.get_topics() if t["id"] == "my_topic")
    assert topic["name"] == "My Topic"


# ---------------------------------------------------------------------------
# reload behaviour
# ---------------------------------------------------------------------------


def test_load_all_clears_previous_data(tmp_path):
    (tmp_path / "First.csv").write_text("word,translation\nfoo,bar\n")
    vm = VocabularyManager(str(tmp_path))
    assert "First" in vm.vocab_sets

    # Remove the file and add a new one, then reload
    (tmp_path / "First.csv").unlink()
    (tmp_path / "Second.csv").write_text("word,translation\nbaz,qux\n")
    vm.load_all()

    assert "First" not in vm.vocab_sets
    assert "Second" in vm.vocab_sets
