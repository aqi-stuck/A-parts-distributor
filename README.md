# Parts Distributor Search

Warehouse staff can search a parts catalog using messy descriptions. The API
returns ranked catalog results with confidence and evidence, or routes uncertain
queries for human review.

See [Checklist.md](Checklist.md) for project roles and remaining work.

## Run with Docker

Install Docker Engine and the Docker Compose plugin, then run these commands
from the repository root:

```bash
docker compose up --build
```

Compose builds and starts the frontend and backend. The backend health check
must pass before the frontend starts.

- Frontend: <http://localhost:8080>
- API health: <http://localhost:8000/health>
- Interactive API docs: <http://localhost:8000/docs>

Press `Ctrl+C` to stop the services. The SQLite database is stored in a named
Docker volume, so it remains available after stopping and restarting the
containers. To stop the services from another terminal, run:

```bash
docker compose down
```

To also delete the saved database and other Compose volumes, run
`docker compose down --volumes`. **This permanently deletes the saved data.**

## Run locally without Docker

Prerequisites: Python 3.12, Node.js 22, and npm.

From the repository root, create a Python environment and install the backend
dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/parts-search/requirements.txt
```

In one terminal, start the API:

```bash
cd backend/parts-search
python -m uvicorn app.main:app --reload
```

In a second terminal, install the frontend dependencies and start Vite:

```bash
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite (usually <http://localhost:5173>). The API
is available at <http://localhost:8000>.

## Project layout

- `frontend/`: React and Vite warehouse interface
- `backend/parts-search/`: FastAPI search API and catalog
- `compose.yaml`: local multi-container setup
- `.github/workflows/ci.yml`: backend tests, frontend build, and Docker image build
