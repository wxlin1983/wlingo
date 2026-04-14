import os

# Change to src/ so relative paths for templates, static, and vocabulary resolve correctly.
# This must happen at module level (before test file imports trigger wlingo package loading).
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
os.chdir(SRC_DIR)


class FakeRedis:
    """In-memory Redis stub: covers get/set/delete used by the router."""

    def __init__(self):
        self._data: dict = {}

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value: str, ex=None):
        self._data[key] = value

    def delete(self, key: str):
        self._data.pop(key, None)
