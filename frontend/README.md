# Next.js Frontend

This folder contains a Next.js frontend for the healthcare compliance platform.

## Run

```powershell
cd C:\Users\Bacancy\healthcare-compliance-platform\frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Pages

- `/` Dashboard
- `/modules`
- `/progress`
- `/notifications`
- `/audit`

## Data source

Current UI uses local Next.js API routes (`app/api/*`) backed by mock payloads in `lib/mock-data.ts`.
You can replace these route handlers to call the Python backend endpoints when exposed over HTTP.

## Backend Proxy Mode

Set `BACKEND_API_BASE_URL` to route API calls through your backend.

Example:

```powershell
$env:BACKEND_API_BASE_URL="http://localhost:8000/api"
npm run dev
```

If backend requests fail, the app falls back to local mock data.
