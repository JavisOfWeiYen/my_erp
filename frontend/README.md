# Frontend — My Sales System

Vite + React + Material-UI + react-i18next.

## Setup

```bash
cd frontend
npm install
cp .env.example .env
```

## Run dev server

```bash
npm run dev
```

Opens http://localhost:5173

## Build / preview

```bash
npm run build
npm run preview
```

## Environment

`.env`:

| Var | Default | Description |
|-----|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API base URL |

## Project layout

```
src/
├── main.jsx          App entry — ThemeProvider, BrowserRouter, i18n init
├── App.jsx           Route definitions
├── theme.js          MUI theme
├── i18n.js           react-i18next setup + supported languages
├── api/
│   └── client.js     Axios instance (auto-attaches JWT from localStorage)
├── locales/
│   ├── zh-TW.json    Traditional Chinese strings
│   └── en.json       English strings
├── components/
│   └── Layout.jsx    Drawer + AppBar shell
└── pages/            Page components (one per route)
```

## Path alias

`@/` resolves to `src/` (see `vite.config.js`). Use it in imports:

```js
import apiClient from '@/api/client'
```

## i18n

- Languages supported: `zh-TW` (default), `en`. Add new ones in `src/locales/` and register in `src/i18n.js`.
- Switch language at runtime via the dropdown in the top AppBar.
- User selection persists in `localStorage`.

## API client

`src/api/client.js` automatically attaches `Authorization: Bearer <token>` from `localStorage.access_token` and clears it on 401.
