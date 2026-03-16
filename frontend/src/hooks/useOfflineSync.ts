import { useState, useEffect } from 'react';
import { syncService } from '../services/syncService';
import { useNetworkStatus } from './useNetworkStatus';

interface SyncStatus {
  isSyncing: boolean;
  hasPendingChanges: boolean;
  lastSyncResult: {
    success: boolean;
    syncedCount: number;
    failedCount: number;
    errors: string[];
  } | null;
}

export const useOfflineSync = () => {
  const { isOnline } = useNetworkStatus();
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    isSyncing: false,
    hasPendingChanges: false,
    lastSyncResult: null
  });

  useEffect(() => {
    // Check for pending changes on mount
    const checkPendingChanges = async () => {
      const hasPending = await syncService.hasPendingChanges();
      setSyncStatus((prev: SyncStatus) => ({ ...prev, hasPendingChanges: hasPending }));
    };

    checkPendingChanges();

    // Register service worker sync
    syncService.registerServiceWorkerSync();

    // Subscribe to sync completion events
    const unsubscribe = syncService.onSyncComplete((result) => {
      setSyncStatus((prev: SyncStatus) => ({
        ...prev,
        isSyncing: false,
        hasPendingChanges: result.failedCount > 0,
        lastSyncResult: result
      }));
    });

    return () => {
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    // Auto-sync when coming back online
    if (isOnline && syncStatus.hasPendingChanges && !syncStatus.isSyncing) {
      manualSync();
    }
  }, [isOnline]);

  const manualSync = async () => {
    if (syncStatus.isSyncing) return;

    setSyncStatus((prev: SyncStatus) => ({ ...prev, isSyncing: true }));

    try {
      const result = await syncService.syncPendingChanges();
      setSyncStatus((prev: SyncStatus) => ({
        ...prev,
        isSyncing: false,
        hasPendingChanges: result.failedCount > 0,
        lastSyncResult: result
      }));
    } catch (error) {
      setSyncStatus((prev: SyncStatus) => ({
        ...prev,
        isSyncing: false,
        lastSyncResult: {
          success: false,
          syncedCount: 0,
          failedCount: 0,
          errors: [error instanceof Error ? error.message : 'Unknown error']
        }
      }));
    }
  };

  return {
    ...syncStatus,
    manualSync
  };
};
