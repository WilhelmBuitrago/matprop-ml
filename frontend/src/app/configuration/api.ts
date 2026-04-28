// frontend/src/app/configuration/api.ts
// API utility functions for the configuration service

import { ENV } from '../../env.client';

const API_BASE_URL = ENV.API_URL;

interface ModelConfig {
  provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  api_key?: string;
  base_url?: string;
}

interface APIConfig {
  host: string;
  port: number;
  debug: boolean;
  cors_origins: string[];
  rate_limit: number;
}

interface ExternalAPIConfig {
  mp_api_key: string | null;
  semantic_scholar_api_key: string | null;
  crossref_email: string | null;
  unpaywall_email: string | null;
  openrouter_api_key: string | null;
  agent_api_key: string | null;
}

interface SystemConfig {
  log_level: string;
  data_dir: string;
  temp_dir: string;
  backup_dir: string;
  max_workers: number;
  timeout: number;
  extra_config: Record<string, any>;
}

interface ConfigSchema {
  models: Record<string, ModelConfig>;
  api: APIConfig;
  external_apis: ExternalAPIConfig;
  system: SystemConfig;
  extra_config: Record<string, any>;
}

/**
 * Fetch current configuration
 * @returns Promise<ConfigSchema>
 */
export async function fetchConfig(): Promise<ConfigSchema> {
  try {
    const response = await fetch(`${API_BASE_URL}/config`);
    if (!response.ok) {
      throw new Error(`Failed to fetch config: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching configuration:', error);
    throw error;
  }
}

/**
 * Update configuration
 * @param config - Configuration to update
 * @returns Promise<boolean>
 */
export async function updateConfig(config: ConfigSchema): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update config: ${response.statusText}`);
    }
    
    return true;
  } catch (error) {
    console.error('Error updating configuration:', error);
    throw error;
  }
}

/**
 * Validate configuration
 * @param config - Configuration to validate
 * @returns Promise<{valid: boolean, errors?: any[]}>
 */
export async function validateConfig(config: ConfigSchema): Promise<{valid: boolean, errors?: any[]}> {
  try {
    const response = await fetch(`${API_BASE_URL}/config/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to validate config: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error validating configuration:', error);
    throw error;
  }
}

/**
 * Fetch configuration history
 * @returns Promise<any[]>
 */
export async function fetchConfigHistory(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/config/history`);
    if (!response.ok) {
      throw new Error(`Failed to fetch config history: ${response.statusText}`);
    }
    const data = await response.json();
    return data.data || [];
  } catch (error) {
    console.error('Error fetching configuration history:', error);
    throw error;
  }
}