import csv
import glob
import logging
import os
import re

from .models import Topic, Word

logger = logging.getLogger(__name__)

_KANA_PATTERN = re.compile(r"[぀-ヿ]")  # hiragana + katakana


def _is_kana_topic(records: list[Word]) -> bool:
    """True if most of a topic's answer keys (translations) contain kana
    characters. Used to decide whether the frontend should offer live
    romaji-to-kana conversion in the spelling-answer input."""
    if not records:
        return False
    kana_count = sum(1 for r in records if _KANA_PATTERN.search(r["translation"]))
    return kana_count > len(records) / 2


# --- Service Layer: Vocabulary Management ---
class VocabularyManager:
    """Manages loading and accessing vocabulary sets."""

    def __init__(self, directory: str) -> None:
        self.directory = directory
        self.vocab_sets: dict[str, list[Word]] = {}
        self.topic_types: dict[str, str] = {}
        self.romaji_input: dict[str, bool] = {}
        self.load_all()

    def load_all(self) -> None:
        self.vocab_sets = {}
        self.topic_types = {}
        self.romaji_input = {}
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
            logger.warning(f"Created directory {self.directory}. Please add CSV files.")
            return

        # Multiple-choice topics live at the top level; spelling (typed-answer)
        # topics live in a "spelling" subdirectory. The subdirectory is never
        # auto-created — it's simply absent (and skipped) until someone adds one.
        self._load_dir(self.directory, "multiple_choice")
        self._load_dir(os.path.join(self.directory, "spelling"), "spelling")

        if not self.vocab_sets:
            logger.warning("No CSV files found. Loading dummy data.")
            self.vocab_sets["default_dummy"] = [
                {"word": "Hund", "translation": "dog", "explanation": ""},
                {"word": "Katze", "translation": "cat", "explanation": ""},
                {"word": "Baum", "translation": "tree", "explanation": ""},
                {"word": "Haus", "translation": "house", "explanation": ""},
                {"word": "Wasser", "translation": "water", "explanation": ""},
            ]

    def _load_dir(self, directory: str, quiz_type: str) -> None:
        csv_files = glob.glob(os.path.join(directory, "*.csv"))
        for file_path in csv_files:
            try:
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                records = self._read_csv(file_path)
                if records is None:
                    logger.error(f"Skipping {file_name}: Missing columns.")
                    continue
                if not records:
                    logger.error(f"Skipping {file_name}: No usable rows.")
                    continue
                self.vocab_sets[file_name] = records
                self.topic_types[file_name] = quiz_type
                if quiz_type == "spelling":
                    self.romaji_input[file_name] = _is_kana_topic(records)
                logger.info(f"Loaded {len(records)} words from {file_name}")
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

    @staticmethod
    def _read_csv(file_path: str) -> list[Word] | None:
        """Parse a vocabulary CSV. Returns None if the required columns are
        missing; rows with an empty word or translation are dropped."""
        with open(file_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            if "word" not in fields or "translation" not in fields:
                return None
            records: list[Word] = []
            for line_num, row in enumerate(reader, start=2):
                word = (row.get("word") or "").strip()
                translation = (row.get("translation") or "").strip()
                if not word or not translation:
                    logger.warning(
                        f"Dropping {file_path} line {line_num}: "
                        "empty word or translation."
                    )
                    continue
                records.append(
                    {
                        "word": word,
                        "translation": translation,
                        "explanation": (row.get("explanation") or "").strip(),
                    }
                )
        return records

    def get_words(self, topic: str) -> list[Word]:
        return self.vocab_sets.get(topic, [])

    def get_quiz_type(self, topic: str) -> str:
        return self.topic_types.get(topic, "multiple_choice")

    def get_romaji_input(self, topic: str) -> bool:
        return self.romaji_input.get(topic, False)

    def get_topics(self) -> list[Topic]:
        topics: list[Topic] = []
        for key, words in self.vocab_sets.items():
            display_name = key.replace("_", " ").title()
            topics.append(
                {
                    "id": key,
                    "name": display_name,
                    "count": len(words),
                    "quiz_type": self.get_quiz_type(key),
                }
            )
        topics.sort(key=lambda x: x["name"])
        return topics
