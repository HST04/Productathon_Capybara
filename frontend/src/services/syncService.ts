import { offlineStorage, PendingChange } from './offlineStorage';
import { leadsAPI } from './api';

interface SyncResult {
  success: boolean;
  syncedCount: number;
  failedCount: number;
  errors: string[];
}

class SyncService {
  private isSyncing = false;
  private syncListeners: Array<(result: SyncResult) => void> = [];

  async syncPendingChanges(): Promise<SyncResult> {
    if (this.isSyncing) {
      return {
        success: false,
        syncedCount: 0,
        failedCount: 0,
        errors: ['Sync already in progress']
      };
    }

    this.isSyncing = true;
    const result: SyncResult = {
      success: true,
      syncedCount: 0,
      failedCount: 0,
      errors: []
    };

    try {
      const pendingChanges = await offlineStorage.getPendingChanges();

      if (pendingChanges.length === 0) {
        this.isSyncing = false;
        return result;
      }

      // Sort by timestamp to maintain order
      pendingChanges.sort((a, b) => a.timestamp - b.timestamp);

      for (const change of pendingChanges) {
        try {
          await this.syncChange(change);
          await offlineStorage.removePendingChange(change.id);
          result.syncedCount++;
        } catch (error) {
          result.failedCount++;
          result.errors.push(`Failed to sync ${change.type} for lead ${change.leadId}: ${error}`);
          console.error('Sync error:', error);
        }
      }

      result.success = result.failedCount === 0;
    } catch (error) {
      result.success = false;
      result.errors.push(`Sync failed: ${error}`);
      console.error('Sync service error:', error);
    } finally {
      this.isSyncing = false;
      this.notifyListeners(result);
    }

    return result;
  }

  private async syncChange(change: PendingChange): Promise<void> {
    switch (change.type) {
      case 'feedback':
        await leadsAPI.submitFeedback(change.leadId, change.data.feedbackType, change.data.notes);
        break;
      
      case 'note':
        await leadsAPI.addLeadNotes(change.leadId, change.data.notes);
        break;
      
      case 'status':
        await leadsAPI.updateLeadStatus(change.leadId, change.data.status);
        break;
      
      default:
        throw new Error(`Unknown change type: ${change.type}`);
    }
  }

  async hasPendingChanges(): Promise<boolean> {
    return await offlineStorage.hasPendingChanges();
  }

  onSyncComplete(callback: (result: SyncResult) => void): () => void {
    this.syncListeners.push(callback);
    
    // Return unsubscribe function
    return () => {
      this.syncListeners = this.syncListeners.filter(cb => cb !== callback);
    };
  }

  private notifyListeners(result: SyncResult): void {
    this.syncListeners.forEach(callback => {
      try {
        callback(result);
      } catch (error) {
        console.error('Sync listener error:', error);
      }
    });
  }

  registerServiceWorkerSync(): void {
    if ('serviceWorker' in navigator && 'sync' in (window as any).ServiceWorkerRegistration.prototype) {
      navigator.serviceWorker.ready.then((registration: any) => {
        // Listen for sync messages from service worker
        navigator.serviceWorker.addEventListener('message', (event) => {
          if (event.data.type === 'SYNC_REQUESTED') {
            this.syncPendingChanges();
          }
        });

        // Register sync event
        registration.sync.register('sync-pending-changes').catch((error: Error) => {
          console.error('Background sync registration failed:', error);
        });
      });
    }
  }
}

export const syncService = new SyncService();
