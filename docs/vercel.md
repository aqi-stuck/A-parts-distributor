# Vercel deployment

The repository supports two Vercel layouts.

## Combined deployment

Keep the repository root as the Vercel project root. The root `vercel.json`
builds the frontend and exposes the FastAPI application under `/api`.

Set no public frontend API host for same-origin deployment:

```text
VITE_API_BASE_URL=/api
```

## Separate deployments

Create one Vercel project for the backend and another for the frontend.

### Backend project

Set the Vercel project Root Directory to:

```text
backend
```

The backend has `vercel.json` in its project root and exposes the API through
the backend Vercel domain.

### Frontend project

Set the Vercel project Root Directory to:

```text
frontend
```

Set the environment variable:

```text
VITE_API_BASE_URL=https://your-backend-project.vercel.app
```

The frontend project has `vercel.json` in its project root. Redeploy after
changing the environment variable.
