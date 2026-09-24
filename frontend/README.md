# Stock Prediction Web Application (Frontend)

Modern React-based frontend for the Stock Price Prediction System built with React 18, TypeScript, Vite, Tailwind CSS, and Recharts.

## Prerequisites

- **Node.js**: 16 or higher
- **npm**: Comes with Node.js
- **Backend**: Ensure backend server is running on `http://localhost:5000`

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

## Project Structure

```
src/
├── components/           # React components (51 components)
│   ├── charts/           # Chart components
│   ├── stock/            # Stock-related components
│   └── ...
├── services/             # API service layer
├── styles/               # Global styles
└── utils/                # Utility functions
```

## Key Features

- Real-time stock price display
- Interactive historical charts (5-year data)
- ML prediction visualization
- Currency conversion (USD/INR)
- Full-text search across 1,001 stocks
- Technical indicator calculations

## Configuration

API base URL is configured in `src/services/stockService.ts`. Backend should be running at:
```
http://localhost:5000
```

## Building for Production

```bash
npm run build
```

Output will be in the `dist/` directory, ready to be served by a web server.

## Troubleshooting

### Port Already in Use
If port 5173 is busy, Vite will automatically use the next available port.

### CORS Errors
Ensure backend server has CORS enabled for `http://localhost:5173`

### Build Fails
- Delete `node_modules` and `package-lock.json`
- Run `npm install` again
- Try rebuilding

## Tech Stack

- **React** 18.3.1 - UI library
- **TypeScript** - Type safety
- **Vite** 6.4.0 - Build tool
- **Tailwind CSS** - Styling
- **Radix UI** - Accessible components
- **Recharts** 2.15.2 - Data visualization