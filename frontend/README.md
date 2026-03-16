# HPCL Lead Intelligence - Frontend

React TypeScript frontend for the HPCL B2B Lead Intelligence Agent.

## Features

- **Lead Management**: View, filter, sort, and manage business opportunity leads
- **Lead Dossier**: Comprehensive lead details with company info, event analysis, and product recommendations
- **Feedback System**: Submit feedback (Accept, Reject, Convert) to improve source trust scoring
- **Dashboard**: View key metrics and top sources
- **Source Registry**: Monitor data sources with dynamic trust scores
- **Mobile-First Design**: Responsive interface optimized for field sales officers
- **Offline Support**: Service Workers + IndexedDB for offline access and background sync

## Technology Stack

- **React 18** with TypeScript
- **React Router** for navigation
- **CSS Modules** for styling
- **Fetch API** for backend communication
- **Service Workers** for offline caching and background sync
- **IndexedDB** for local data persistence

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Backend API running at `http://localhost:8000`

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The app will open at `http://localhost:3000`.

**Note**: The backend API must be running at `http://localhost:8000` for the frontend to function properly. The `package.json` includes a proxy configuration that forwards API requests to the backend.

### Environment Variables

Create a `.env` file in the frontend directory (optional):

```env
REACT_APP_API_URL=http://localhost:8000
```

**Note**: The `package.json` includes a `proxy` field that automatically forwards API requests to `http://localhost:8000` during development, so the `.env` file is optional for local development.

## Project Structure

```
src/
├── components/          # React components
│   ├── LeadList.tsx    # Lead list with filters and pagination
│   ├── LeadDossier.tsx # Detailed lead view
│   ├── FeedbackModal.tsx # Feedback submission modal
│   ├── Dashboard.tsx   # Dashboard with metrics
│   ├── SourceRegistry.tsx # Source management
│   ├── Navigation.tsx  # Navigation bar
│   ├── NewLeadsQueue.tsx # Mobile-first new leads view
│   ├── LeadNotes.tsx   # Lead notes functionality
│   ├── MobileActionBar.tsx # Mobile action buttons
│   ├── LowBandwidthMode.tsx # Low bandwidth detection
│   └── SyncStatusIndicator.tsx # Offline sync status
├── services/           # API client and offline support
│   ├── api.ts         # Backend API integration
│   ├── offlineStorage.ts # IndexedDB wrapper
│   └── syncService.ts # Background sync manager
├── hooks/             # Custom React hooks
│   ├── useNetworkStatus.ts # Network detection
│   └── useOfflineSync.ts # Offline sync hook
├── types/             # TypeScript type definitions
│   └── index.ts       # Data models
├── App.tsx            # Main app component with routing
└── index.tsx          # App entry point
public/
└── service-worker.js  # Service worker for offline support
```

## Available Scripts

### `npm start`

Runs the app in development mode at [http://localhost:3000](http://localhost:3000).

### `npm test`

Launches the test runner in interactive watch mode.

### `npm run build`

Builds the app for production to the `build` folder.

## API Integration

The frontend communicates with the FastAPI backend at `localhost:8000`. Key endpoints:

- `GET /api/leads` - List leads with filters and pagination
- `GET /api/leads/{id}` - Get lead dossier
- `POST /api/leads/{id}/feedback` - Submit feedback
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/sources` - Source registry

## Design System

### Colors

- **Primary**: HPCL Red (#e31e24)
- **Priority High**: Red (#f44336)
- **Priority Medium**: Orange (#ff9800)
- **Priority Low**: Green (#4caf50)

### Typography

- **Font Family**: System fonts (-apple-system, BlinkMacSystemFont, Segoe UI, Roboto)
- **Headings**: 600-700 weight
- **Body**: 400 weight, 1.6 line-height

### Spacing

- **XS**: 4px
- **SM**: 8px
- **MD**: 16px
- **LG**: 24px
- **XL**: 32px

## Mobile Optimization

The interface is mobile-first with responsive breakpoints:

- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

Key mobile features:
- Touch-optimized buttons and controls
- Collapsible navigation
- Simplified table views
- One-tap actions (call, email, schedule)

## Offline Support

The application includes comprehensive offline functionality for field sales officers:

### Service Worker Features

- **Static Asset Caching**: Automatically caches HTML, CSS, and JavaScript files for offline access
- **API Response Caching**: Caches API responses with network-first strategy
- **Background Sync**: Queues changes made offline and syncs when connection is restored
- **Cache Management**: Automatically cleans up old cache versions

### Offline Capabilities

- **View Cached Leads**: Access previously viewed leads while offline
- **Submit Feedback Offline**: Feedback is queued and submitted when online
- **Add Notes Offline**: Lead notes are stored locally and synced later
- **Update Lead Status**: Status changes are queued for background sync
- **Network Status Detection**: Visual indicators for online/offline/slow connection states
- **Low Bandwidth Mode**: Optimized UI for slow connections (2G/3G)

### IndexedDB Storage

The app uses IndexedDB for local data persistence:
- **Lead Cache**: Stores lead data for offline viewing (7-day retention)
- **Pending Changes**: Queues feedback, notes, and status updates for sync
- **Automatic Cleanup**: Removes old cached data to manage storage

### How It Works

1. **Online**: Data fetched from API and cached in IndexedDB
2. **Offline**: App serves cached data and queues changes locally
3. **Back Online**: Background sync automatically submits queued changes
4. **Sync Status**: Visual indicator shows sync progress and pending changes

The service worker is automatically registered when the app loads. No additional configuration is required.

## Future Enhancements

- [ ] Service Workers for offline support
- [ ] IndexedDB for local data caching
- [ ] Push notifications
- [ ] Advanced filtering and search
- [ ] Lead notes and activity timeline
- [ ] Export functionality
- [ ] Dark mode

## Contributing

Follow the project's coding conventions:
- Use TypeScript for type safety
- Follow React best practices
- Write mobile-first responsive CSS
- Keep components focused and reusable
- Add comments for complex logic

## License

Internal HPCL project - All rights reserved
