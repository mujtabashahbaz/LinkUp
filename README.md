# LinkUp — Full-Stack LinkedIn-Style Clone

A GitHub-ready full-stack social/professional networking MVP.

## Features

- Register and sign in with JWT authentication
- Professional profiles
- Create posts
- Feed
- Likes and comments
- Discover users
- Send and accept connection requests
- Responsive React interface
- FastAPI REST backend
- SQLite locally / PostgreSQL in production

## Project structure

```text
linkup_github_ready/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── index.html
│   ├── vercel.json
│   └── .env.example
├── .gitignore
├── render.yaml
└── README.md
```

## Run locally

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Backend API docs:

```text
http://localhost:8000/docs
```

### Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

## Upload to GitHub

Create a new empty GitHub repository, then from this project's root directory:

```bash
git init
git add .
git commit -m "Initial LinkUp full-stack app"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

## Deploy backend + PostgreSQL on Render

This repository includes `render.yaml`.

1. Connect your GitHub repository to Render.
2. Create a Blueprint from the repository.
3. Render can create the API service and PostgreSQL database from `render.yaml`.
4. Set the `FRONTEND_URL` environment variable after your Vercel frontend is deployed.
5. Copy the public Render backend URL.

The backend reads these environment variables:

```text
DATABASE_URL
SECRET_KEY
FRONTEND_URL
```

Do not commit real secrets to GitHub.

## Deploy frontend on Vercel

Import the same GitHub repository into Vercel.

Set the Root Directory to:

```text
frontend
```

Add this environment variable:

```text
VITE_API_URL=https://YOUR-RENDER-BACKEND-URL
```

Deploy the project.

After Vercel gives you the frontend URL, return to Render and set:

```text
FRONTEND_URL=https://YOUR-VERCEL-FRONTEND-URL
```

Redeploy/restart the backend if necessary.

## Local environment files

The included `.env.example` files document the expected variables. Copy them to
`.env` if you want local environment configuration. `.env` files are ignored by Git.

## Production considerations

This is an MVP. Before serious production use, add database migrations, refresh
tokens, email verification, password reset, media/object storage, rate limiting,
automated tests, logging/monitoring, moderation and stronger security controls.
