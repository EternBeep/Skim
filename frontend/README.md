# Skim Frontend

Monochrome React UI for [Skim](../README.md) — semantic YouTube video search.

## Local dev

```bash
npm install
npm run dev
```

Backend defaults to `http://localhost:8000`. Override with `.env`:

```
VITE_API_BASE_URL=http://localhost:8000
```

## Deploy to Vercel

1. Import this repo in [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Add environment variable:
   - `VITE_API_BASE_URL` = your backend URL (e.g. Hugging Face Space)
4. Deploy — `vercel.json` handles SPA routing.

Build command: `npm run build` · Output: `dist`

## Stack

- React 19 + Vite 8
- Framer Motion (animations)
- Lucide React (icons)
- Monochrome design tokens in `src/index.css`
