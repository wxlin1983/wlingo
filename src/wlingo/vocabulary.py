import glob
import logging
import os

import pandas as pd

from .models import Topic, Word

logger = logging.getLogger(__name__)


# --- Service Layer: Vocabulary Management ---
class VocabularyManager:
    """Manages loading and accessing vocabulary sets."""

    def __init__(self, directory: str) -> None:
        self.directory = directory
        self.vocab_sets: dict[str, list[Word]] = {}
        self.topic_types: dict[str, str] = {}
        self.load_all()

    def load_all(self) -> None:
        self.vocab_sets = {}
        self.topic_types = {}
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
                df = pd.read_csv(file_path, encoding="utf-8")
                if "word" in df.columns and "translation" in df.columns:
                    if "explanation" in df.columns:
                        df["explanation"] = df["explanation"].fillna("")
                    else:
                        df["explanation"] = ""
                    self.vocab_sets[file_name] = df.to_dict("records")
                    self.topic_types[file_name] = quiz_type
                    logger.info(f"Loaded {len(df)} words from {file_name}")
                else:
                    logger.error(f"Skipping {file_name}: Missing columns.")
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

    def get_words(self, topic: str) -> list[Word]:
        return self.vocab_sets.get(topic, [])

    def get_quiz_type(self, topic: str) -> str:
        return self.topic_types.get(topic, "multiple_choice")

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
