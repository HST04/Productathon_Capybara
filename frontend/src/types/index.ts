// Type definitions for HPCL Lead Intelligence Agent

export interface Source {
  id: string;
  domain: string;
  category: 'news' | 'tender' | 'company_site';
  access_method: 'rss' | 'api' | 'scrape';
  crawl_frequency_minutes: number;
  trust_score: number;
  trust_tier: 'high' | 'medium' | 'low' | 'neutral';
  robots_txt_allowed: boolean;
  last_crawled_at?: string;
  created_at: string;
}

export interface Company {
  id: string;
  name: string;
  name_variants: string[];
  cin?: string;
  gst?: string;
  website?: string;
  industry?: string;
  address?: string;
  locations: string[];
  key_products: string[];
  phone?: string;
  email?: string;
  created_at: string;
  updated_at: string;
}

export interface Event {
  id: string;
  signal_id: string;
  company_id: string;
  event_type?: string;
  event_summary: string;
  location?: string;
  capacity?: string;
  deadline?: string;
  intent_strength?: number;
  is_lead_worthy: boolean;
  created_at: string;
}

export interface ProductRecommendation {
  id: string;
  lead_id: string;
  product_name: string;
  confidence_score: number;
  reasoning: string;
  reason_code: string;
  rank: number;
  uncertainty_flag: boolean;
}

export interface Lead {
  id: string;
  event_id: string;
  company_id: string;
  score: number;
  priority: 'high' | 'medium' | 'low';
  assigned_to?: string;
  territory?: string;
  status: 'new' | 'contacted' | 'qualified' | 'converted' | 'rejected';
  created_at: string;
  updated_at: string;
  // Populated fields
  company?: Company;
  event?: Event;
  products?: ProductRecommendation[];
  source_links?: string[];
}

export interface Feedback {
  id: string;
  lead_id: string;
  feedback_type: 'accepted' | 'rejected' | 'converted';
  notes?: string;
  submitted_at: string;
  submitted_by?: string;
}

export interface Note {
  id: string;
  lead_id: string;
  content: string;
  created_at: string;
  created_by?: string;
}

export interface LeadDossier extends Lead {
  company: Company;
  event: Event;
  products: ProductRecommendation[];
  source_links: string[];
  suggested_action?: string;
  notes?: Note[];
}

export interface DashboardStats {
  total_leads: number;
  high_priority_leads: number;
  medium_priority_leads: number;
  low_priority_leads: number;
  conversion_rate: number;
  top_sources: Array<{
    domain: string;
    trust_score: number;
    lead_count: number;
  }>;
}

export interface LeadFilters {
  priority?: 'high' | 'medium' | 'low';
  status?: 'new' | 'contacted' | 'qualified' | 'converted' | 'rejected';
  date_from?: string;
  date_to?: string;
  search?: string;
}

export interface PaginationParams {
  page: number;
  page_size: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
