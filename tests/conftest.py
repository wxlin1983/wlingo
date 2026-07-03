import os

# Change to src/ so relative paths for templates, static, and vocabulary resolve correctly.
# This must happen at module level (before test file imports trigger wlingo package loading).
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
os.chdir(SRC_DIR)
