# Spinify Web

React (Vite + TypeScript + Tailwind) frontend for Spinify. Minimal UI with Spotify green accents.

## Setup

```bash
npm install
```

## Dev

Start the Spinify API first (from repo root: `python -m spinify.main`), then:

```bash
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to `http://localhost:8000`.

## Build

```bash
npm run build
```

Output in `dist/`. Serve with any static host or mount under the FastAPI app.

## Env

- `VITE_API_URL` – API base URL (default: empty, so same-origin/proxy is used).
