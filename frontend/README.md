# Sentinel Frontend

React + TypeScript frontend for the Sentinel Cross-Commodity Signal Dashboard.

## Setup

1. **Install dependencies:**
```bash
npm install
```

2. **Start development server:**
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Features

- **Signals Table**: View all signals with filtering, sorting, and search
- **Market Detail Pages**: Detailed view of signals for each market with charts
- **Watchlists**: Create and manage watchlists for signals and markets
- **Alerts**: Monitor signal changes and conditions

## Tech Stack

- React 18
- TypeScript
- Vite
- React Router
- Recharts (for data visualization)

## API Integration

The frontend connects to the backend API running on `http://localhost:8000` via a proxy configured in `vite.config.ts`.

## Build

```bash
npm run build
```

This creates a production build in the `dist/` directory.

