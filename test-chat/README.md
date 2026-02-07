# Trade Mind Chat Interface

A simple chat interface for the Trade Mind AI Negotiation Engine using React, Vite, and Tailwind CSS.

## Features

- Real-time chat interface with user and bot messages
- Neo-brutalist design matching the main frontend
- Automatic session creation and management
- Backend API integration
- Responsive design for mobile and desktop
- Message history and timestamps
- Health check for backend connectivity

## Setup

### Prerequisites

- Node.js 16+ and npm/yarn
- Python backend running at `http://127.0.0.1:8000`

### Installation

```bash
cd test-chat
npm install
```

### Running Locally

**Terminal 1: Start the backend**
```bash
cd backend
python -m uvicorn src.server:app --reload
```

**Terminal 2: Start the chat interface**
```bash
cd test-chat
npm run dev
```

The application will be available at `http://localhost:5173`

## Project Structure

```
test-chat/
├── src/
│   ├── Chat.jsx           # Main chat component
│   ├── Chat.css           # Chat-specific styles
│   ├── App.jsx            # Main app component
│   ├── api.js             # API utility functions
│   ├── index.css          # Global styles
│   └── main.jsx           # React entry point
├── index.html             # HTML template
├── package.json           # Dependencies
├── vite.config.js         # Vite configuration
├── tailwind.config.js     # Tailwind CSS configuration
└── postcss.config.js      # PostCSS configuration
```

## Color Scheme (Neo-Brutalist)

- **Navy**: #001524 (Primary)
- **Teal**: #15616D (Secondary)
- **Cream**: #FFECD1 (Background)
- **Orange**: #FF7D00 (Accent)
- **Maroon**: #78290F (Alert)

## API Endpoints

The chat interface communicates with the backend API:

- `POST /api/v1/negotiate/session` - Create new session
- `POST /api/v1/negotiate/converse` - Send message
- `GET /api/v1/negotiate/session/:id` - Get session details
- `GET /api/v1/negotiate/health` - Health check

## Deployment

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

## Troubleshooting

### Backend Connection Failed
- Ensure the backend is running: `python -m uvicorn src.server:app --reload`
- Check that it's running on `http://127.0.0.1:8000`
- Look for CORS errors in the browser console

### Messages Not Sending
- Check the browser console for API errors
- Verify the session ID is valid
- Ensure the backend API is responding correctly

## License

MIT
