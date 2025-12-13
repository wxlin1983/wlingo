import glob
import logging
import os
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


# --- Service Layer: Vocabulary Management ---
class VocabularyManager:
    """Manages loading and accessing vocabulary sets."""

    def __init__(self, directory: str):
        self.directory = directory
        self.vocab_sets: Dict[str, List[Dict[str, str]]] = {}
        self.load_all()

    def load_all(self):
        self.vocab_sets = {}
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
            logger.warning(f"Created directory {self.directory}. Please add CSV files.")
            return

        csv_files = glob.glob(os.path.join(self.directory, "*.csv"))
        for file_path in csv_files:
            try:
                file_name = os.path.splitext(os.path.basename(file_path))[0]
                df = pd.read_csv(file_path, encoding="utf-8")
                if "word" in df.columns and "translation" in df.columns:
                    self.vocab_sets[file_name] = df.to_dict("records")
                    logger.info(f"Loaded {len(df)} words from {file_name}")
                else:
                    logger.error(f"Skipping {file_name}: Missing columns.")
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        if not self.vocab_sets:
            logger.warning("No CSV files found. Loading dummy data.")
            self.vocab_sets["default_dummy"] = [
                {"word": "Hund", "translation": "dog"},
                {"word": "Katze", "translation": "cat"},
                {"word": "Baum", "translation": "tree"},
                {"word": "Haus", "translation": "house"},
                {"word": "Wasser", "translation": "water"},
            ]

    def get_words(self, topic: str) -> List[Dict[str, str]]:
        return self.vocab_sets.get(topic, [])

    def get_topics(self) -> List[Dict[str, Any]]:
        topics = []
        for key, words in self.vocab_sets.items():
            display_name = key.replace("_", " ").title()
            topics.append({"id": key, "name": display_name, "count": len(words)})
        topics.sort(key=lambda x: x["name"])
        return topics
