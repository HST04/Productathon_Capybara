import React from 'react';
import { useOfflineSync } from '../hooks/useOfflineSync';
import './SyncStatusIndicator.css';

export const SyncStatusIndicator: React.FC = () => {
  const { isSyncing, hasPendingChanges, lastSyncResult, manualSync } = useOfflineSync();

  if (!hasPendingChanges && !isSyncing && !lastSyncResult) {
    return null;
  }

  return (
    <div className="sync-status-indicator">
      {isSyncing && (
        <div className="sync-status syncing">
          <span className="sync-icon spinning">🔄</span>
          <span>Syncing changes...</span>
        </div>
      )}

      {!isSyncing && hasPendingChanges && (
        <div className="sync-status pending">
          <span className="sync-icon">⏳</span>
          <span>Changes pending sync</span>
          <button onClick={manualSync} className="sync-button">
            Sync Now
          </button>
        </div>
      )}

      {!isSyncing && lastSyncResult && lastSyncResult.success && (
        <div className="sync-status success">
          <span className="sync-icon">✅</span>
          <span>Synced {lastSyncResult.syncedCount} change(s)</span>
        </div>
      )}

      {!isSyncing && lastSyncResult && !lastSyncResult.success && (
        <div className="sync-status error">
          <span className="sync-icon">❌</span>
          <span>Sync failed: {lastSyncResult.failedCount} error(s)</span>
          <button onClick={manualSync} className="sync-button">
            Retry
          </button>
        </div>
      )}
    </div>
  );
};
