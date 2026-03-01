# Spinify Web

React (Vite + TypeScript + Tailwind) frontend for Spinify. Minimal UI with Spotify green accents. Dashboard shows current record and playback state, and polls the tone-arm sync endpoint so the platter and tone-arm stay in sync with Spotify (e.g. when you pause from another device). Connect supports manual login (paste redirect URL) for setups where the OAuth redirect cannot hit the device (e.g. Pi without HTTPS).

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

Output in `dist/`. Serve with any static host or mount under the FastAPI app. Use `npm run preview` to preview the production build locally.

## Env

- `VITE_API_URL` – API base URL (default: empty, so same-origin/proxy is used).
