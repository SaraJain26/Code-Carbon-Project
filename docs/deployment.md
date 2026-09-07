# Code-Carbon Deployment Guide

This guide details the steps to build, run, and deploy Code-Carbon as a single containerized application.

---

## 1. Unified Architecture Overview

Code-Carbon is designed to be deployed as a single, unified web application:
- **Frontend React Dashboard**: Built during the Docker build stage and output to `dashboard/dist`.
- **Backend FastAPI Service**: Serves the REST API routes and also mounts the `dashboard/dist` folder to serve the static frontend files and handle client-side Single Page Application (SPA) routing fallback.

This unified approach running on a single port eliminates Cross-Origin Resource Sharing (CORS) concerns, simplifies domain mappings, and allows you to run Code-Carbon on standard PaaS platforms (Render, Fly.io, Heroku) under a single web service.

---

## 2. Environment Leak Prevention & `.dockerignore`

> [!IMPORTANT]
> To prevent leaking local API keys and configurations into public or container registry Docker images, the `.dockerignore` file explicitly excludes:
> - `.env`
> - `node_modules/` and `dashboard/node_modules/` (saves build context size)
> - `dashboard/dist/` (prevents stale local builds from being packaged)
>
> All configuration (e.g. `ELECTRICITYMAPS_API_KEY`) must be supplied via runtime environment variables.

---

## 3. Route Registration Order (Implementation Note)

> [!WARNING]
> In FastAPI, route registration order matters. The static file mount and catch-all SPA route are registered at the **very end** of [main.py](file:///d:/Code-Carbon-Project/src/api/main.py) to avoid shadowing:
> 1. Explicit API endpoints (`/health`, `/analyze`, `/zones`, `/search-zones`).
> 2. Auto-generated interactive documentation paths (`/docs`, `/redoc`, `/openapi.json`).
>
> If you add new API endpoints in the future, ensure they are registered **before** the static files section at the bottom of the file.

---

## 4. Local Deployment with Docker

### Prerequisites
- Docker installed on your host machine.
- Optional: Docker Compose.

### Option A: Build and Run via Docker Compose (Recommended)
Use Docker Compose to build and run the image with your `.env` file environment variables loaded automatically:
```bash
docker compose up --build
```
This boots Code-Carbon on `http://localhost:8000`.

### Option B: Build and Run via Docker CLI
1. Build the Docker image:
   ```bash
   docker build -t code-carbon .
   ```
2. Run the container and inject your host `.env` file variables:
   ```bash
   docker run -p 8000:8000 --env-file .env code-carbon
   ```

---

## 5. Deployment to PaaS Platforms

### Deploying to Render
1. Create a new **Web Service** on Render and connect your GitHub repository.
2. Select **Docker** as the Runtime environment.
3. Under **Advanced**, add the environment variable `ELECTRICITYMAPS_API_KEY` with your token.
4. Render will automatically detect the `Dockerfile` in the root directory, build it, and run the readiness check hitting `/health`.

### Deploying to Fly.io
1. Initialize a Fly app from the root folder:
   ```bash
   fly launch
   ```
2. Follow the prompts. Fly will detect the Dockerfile.
3. Set your secret API key:
   ```bash
   fly secrets set ELECTRICITYMAPS_API_KEY=your_token
   ```
4. Deploy the application:
   ```bash
   fly deploy
   ```

---

## 6. Verification and Testing

### Automated Checks
Run the unit test suite locally to verify Python AST analysis and fuzzy sustainability metrics logic:
```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

### Manual Verification Instructions
After the container is running on `http://localhost:8000`:
1. **Interactive Docs**: Open `http://localhost:8000/docs` in your browser. Verify the FastAPI Swagger UI loaded correctly.
2. **Health Check**: Visit `http://localhost:8000/health` and verify you receive `{"status": "healthy"}`.
3. **Frontend Dashboard**: Open `http://localhost:8000/` and verify the dark-themed glassmorphic Code-Carbon dashboard loads.
4. **SPA Catch-All Route**: Access a non-existent frontend route like `http://localhost:8000/some/random/path`. Verify that it cleanly loads the React dashboard (HTTP status `200`) rather than returning a default FastAPI `404 Not Found` page.
5. **AST File Upload**: Go to the `/analyze` tab, drag and drop a python file, select a grid zone, and verify that the analysis reports carbon metrics successfully.
