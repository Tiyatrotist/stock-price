# Stock Price Frontend

React + Vite frontend for the stock-price application.

## Requirements

- Node.js and npm
- The backend API running locally or at a configured URL

## Environment

Create a local environment file when you need to point the frontend at a non-default backend:

```env
VITE_API_BASE_URL=http://localhost:5000
```

`VITE_API_BASE_URL` controls the base URL used by the frontend API service. Keep machine-specific values in local environment files rather than committing them.

## Development

Install dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Create a production build:

```bash
npm run build
```

Run the linter:

```bash
npm run lint
```

## Source layout

- `src/components/` — reusable React UI components.
- `src/services/` — API and network-facing service modules.
- `src/utils/` — shared formatting, conversion, and helper functions.
- `src/assets/` — static assets imported by the application.

The application entry point and top-level page composition live under `src/`.
