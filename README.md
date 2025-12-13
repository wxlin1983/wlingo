# wlingo - A Vocabulary Quiz App

wlingo is a web application that helps you learn new vocabulary through a simple, interactive quiz.

## Getting Started

You can run this application either directly on your machine using Python or with Docker.

### Prerequisites

- Python 3.11+
- `uv` (or `pip`) for package installation
- Docker (optional, for containerized deployment)

### 1. Installation & Setup

First, clone the repository to your local machine:

```bash
git clone https://github.com/your-username/wlingo.git
cd wlingo
```

Next, install the required Python packages. It is recommended to use a virtual environment.

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies using uv (faster)
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### 2. Running the Application

#### Without Docker

To run the app directly, use `uvicorn`:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag automatically restarts the server when you make code changes.

#### With Docker

If you prefer using Docker, you can build and run a container.

1.  **Build the Docker Image:**

    ```bash
    docker build -t wlingo .
    ```

2.  **Run the Container:**

    ```bash
    docker run -d -p 8000:8000 --name wlingo-instance wlingo
    ```

### 3. Accessing the Application

Once the server is running, you can access the application in your web browser:

-   **Start Quiz:** [http://localhost:8000](http://localhost:8000)
-   **API Docs (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)

## 🎨 Customization

To use your own set of vocabulary words, simply edit the `src/vocabulary/words.csv` file. The format is a simple CSV with two columns: `word` and `translation`.

| word  | translation |
| :---- | :---------- |
| Hund  | dog         |
| Katze | cat         |
| Baum  | tree        |
