// API client for HPCL Lead Intelligence backend

import {
  Lead,
  LeadDossier,
  Feedback,
  Company,
  Source,
  DashboardStats,
  LeadFilters,
  PaginationParams,
  PaginatedResponse,
  Note,
} from '../types';
import { offlineStorage } from './offlineStorage';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

async function fetchJSON<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        response.status,
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    // Network error - might be offline
    throw new Error(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

// Lead Management API
export const leadsAPI = {
  /**
   * Get paginated list of leads with optional filters
   */
  async getLeads(
    filters?: LeadFilters,
    pagination?: PaginationParams
  ): Promise<PaginatedResponse<Lead>> {
    const params = new URLSearchParams();
    
    if (filters?.priority) params.append('priority', filters.priority);
    if (filters?.status) params.append('status', filters.status);
    if (filters?.date_from) params.append('date_from', filters.date_from);
    if (filters?.date_to) params.append('date_to', filters.date_to);
    if (filters?.search) params.append('search', filters.search);
    
    if (pagination?.page) params.append('page', pagination.page.toString());
    if (pagination?.page_size) params.append('page_size', pagination.page_size.toString());
    if (pagination?.sort_by) params.append('sort_by', pagination.sort_by);
    if (pagination?.sort_order) params.append('sort_order', pagination.sort_order);

    const queryString = params.toString();
    const endpoint = `/api/leads${queryString ? `?${queryString}` : ''}`;
    
    return fetchJSON<PaginatedResponse<Lead>>(endpoint);
  },

  /**
   * Get complete lead dossier by ID
   */
  async getLeadDossier(leadId: string): Promise<LeadDossier> {
    try {
      const dossier = await fetchJSON<LeadDossier>(`/api/leads/${leadId}`);
      // Cache the lead data for offline access
      await offlineStorage.cacheLead(leadId, dossier);
      return dossier;
    } catch (error) {
      // If offline, try to get from cache
      if (!navigator.onLine) {
        const cached = await offlineStorage.getCachedLead(leadId);
        if (cached) {
          return cached;
        }
      }
      throw error;
    }
  },

  /**
   * Submit feedback for a lead
   */
  async submitFeedback(
    leadId: string,
    feedbackType: 'accepted' | 'rejected' | 'converted',
    notes?: string
  ): Promise<Feedback> {
    try {
      return await fetchJSON<Feedback>(`/api/leads/${leadId}/feedback`, {
        method: 'POST',
        body: JSON.stringify({
          feedback_type: feedbackType,
          notes,
        }),
      });
    } catch (error) {
      // If offline, queue the change for later sync
      if (!navigator.onLine) {
        await offlineStorage.addPendingChange({
          type: 'feedback',
          leadId,
          data: { feedbackType, notes }
        });
        // Return a placeholder response
        return {
          id: 'pending',
          lead_id: leadId,
          feedback_type: feedbackType,
          notes,
          submitted_at: new Date().toISOString(),
          submitted_by: 'current_user'
        } as Feedback;
      }
      throw error;
    }
  },

  /**
   * Update lead status
   */
  async updateLeadStatus(
    leadId: string,
    status: Lead['status']
  ): Promise<Lead> {
    try {
      return await fetchJSON<Lead>(`/api/leads/${leadId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
    } catch (error) {
      // If offline, queue the change for later sync
      if (!navigator.onLine) {
        await offlineStorage.addPendingChange({
          type: 'status',
          leadId,
          data: { status }
        });
        // Return a placeholder - the UI should handle this gracefully
        throw new Error('Status update queued for sync when online');
      }
      throw error;
    }
  },

  /**
   * Add notes to a lead
   */
  async addLeadNotes(leadId: string, notes: string): Promise<Lead> {
    try {
      return await fetchJSON<Lead>(`/api/leads/${leadId}/notes`, {
        method: 'POST',
        body: JSON.stringify({ notes }),
      });
    } catch (error) {
      // If offline, queue the change for later sync
      if (!navigator.onLine) {
        await offlineStorage.addPendingChange({
          type: 'note',
          leadId,
          data: { notes }
        });
        // Return a placeholder
        throw new Error('Note queued for sync when online');
      }
      throw error;
    }
  },

  /**
   * Get notes for a lead
   */
  async getLeadNotes(leadId: string): Promise<Note[]> {
    return fetchJSON<Note[]>(`/api/leads/${leadId}/notes`);
  },
};

// Company API
export const companiesAPI = {
  /**
   * Get company card by ID
   */
  async getCompany(companyId: string): Promise<Company> {
    return fetchJSON<Company>(`/api/companies/${companyId}`);
  },
};

// Source Registry API
export const sourcesAPI = {
  /**
   * Get all sources
   */
  async getSources(): Promise<Source[]> {
    return fetchJSON<Source[]>('/api/sources');
  },

  /**
   * Configure source settings
   */
  async configureSource(
    sourceId: string,
    settings: Partial<Pick<Source, 'crawl_frequency_minutes'>>
  ): Promise<Source> {
    return fetchJSON<Source>(`/api/sources/${sourceId}/configure`, {
      method: 'POST',
      body: JSON.stringify(settings),
    });
  },
};

// Dashboard API
export const dashboardAPI = {
  /**
   * Get dashboard statistics
   */
  async getStats(dateFrom?: string, dateTo?: string): Promise<DashboardStats> {
    const params = new URLSearchParams();
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    
    const queryString = params.toString();
    const endpoint = `/api/dashboard/stats${queryString ? `?${queryString}` : ''}`;
    
    return fetchJSON<DashboardStats>(endpoint);
  },
};

export { APIError };
