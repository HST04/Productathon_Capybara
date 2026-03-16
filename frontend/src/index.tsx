import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { offlineStorage } from './services/offlineStorage';

// Initialize offline storage
offlineStorage.init().catch(console.error);

// Clean up old cached data (older than 7 days) on startup
offlineStorage.clearOldCache().catch(console.error);

// Register service worker for offline support
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then((registration) => {
        console.log('Service Worker registered:', registration);
      })
      .catch((error) => {
        console.error('Service Worker registration failed:', error);
      });
  });
}

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
