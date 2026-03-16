import React from 'react';
import { useNetworkStatus } from '../hooks/useNetworkStatus';
import './LowBandwidthMode.css';

interface LowBandwidthModeProps {
  children: React.ReactNode;
}

export const LowBandwidthMode: React.FC<LowBandwidthModeProps> = ({ children }) => {
  const { isOnline, isSlowConnection } = useNetworkStatus();

  return (
    <div className={`app-container ${isSlowConnection ? 'low-bandwidth' : ''}`}>
      {!isOnline && (
        <div className="offline-banner">
          <span className="offline-icon">⚠️</span>
          <span>You are offline. Changes will sync when connection is restored.</span>
        </div>
      )}
      {isOnline && isSlowConnection && (
        <div className="slow-connection-banner">
          <span className="slow-icon">🐌</span>
          <span>Slow connection detected. Low bandwidth mode enabled.</span>
        </div>
      )}
      {children}
    </div>
  );
};
