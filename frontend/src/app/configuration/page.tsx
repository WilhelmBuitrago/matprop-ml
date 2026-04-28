"use client";

import { useState, useEffect, ChangeEvent, FormEvent } from "react";
import { fetchConfig, updateConfig, validateConfig } from "./api";
import HistoryView from "./history";

// Define TypeScript interfaces for our configuration
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

export default function ConfigurationPage() {
  const [config, setConfig] = useState<ConfigSchema | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{valid: boolean, errors?: any[]} | null>(null);
  const [activeTab, setActiveTab] = useState("models");
  
  // Fetch configuration on component mount
  useEffect(() => {
    const loadConfig = async () => {
      try {
        setLoading(true);
        const configData = await fetchConfig();
        setConfig(configData);
      } catch (error) {
        console.error("Failed to load configuration:", error);
      } finally {
        setLoading(false);
      }
    };

    loadConfig();
  }, []);

  // Handle input changes
  const handleModelChange = (modelName: string, field: keyof ModelConfig, value: string | number) => {
    if (!config) return;
    
    setConfig({
      ...config,
      models: {
        ...config.models,
        [modelName]: {
          ...config.models[modelName],
          [field]: value
        }
      }
    });
  };

  const handleAPIChange = (field: string, value: string | number | boolean) => {
    if (!config) return;
    
    setConfig({
      ...config,
      api: {
        ...config.api,
        [field]: value
      }
    });
  };

  const handleExternalAPIChange = (field: string, value: string) => {
    if (!config) return;
    
    setConfig({
      ...config,
      external_apis: {
        ...config.external_apis,
        [field]: value || null
      }
    });
  };

  const handleSystemChange = (field: string, value: string | number) => {
    if (!config) return;
    
    setConfig({
      ...config,
      system: {
        ...config.system,
        [field]: value
      }
    });
  };

  // Handle form submission
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!config) return;
    
    try {
      setSaving(true);
      await updateConfig(config);
      alert("Configuration saved successfully!");
    } catch (error) {
      console.error("Failed to save configuration:", error);
      alert("Failed to save configuration");
    } finally {
      setSaving(false);
    }
  };

  // Handle validation
  const handleValidate = async () => {
    if (!config) return;
    
    try {
      setValidating(true);
      const result = await validateConfig(config);
      setValidationResult(result);
      
      if (result.valid) {
        alert("Configuration is valid!");
      } else {
        alert(`Configuration has ${result.errors?.length || 0} errors. Please check the validation results.`);
      }
    } catch (error) {
      console.error("Failed to validate configuration:", error);
      alert("Failed to validate configuration");
    } finally {
      setValidating(false);
    }
  };

  if (loading) {
    return (
      <main className="configuration-page">
        <div className="panel">
          <h1>Configuración</h1>
          <p>Cargando configuración...</p>
        </div>
        <style jsx>{`
          .configuration-page {
            height: 100vh;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: clamp(24px, 6vw, 60px);
            background: radial-gradient(circle at top, rgba(109, 93, 252, 0.28), transparent 55%),
              radial-gradient(circle at bottom, rgba(80, 54, 239, 0.22), transparent 60%),
              #050505;
            color: #f4f4f4;
          }

          .panel {
            max-width: 560px;
            width: 100%;
            background: rgba(12, 12, 12, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            padding: clamp(24px, 4vw, 40px);
            box-shadow: 0 20px 55px rgba(0, 0, 0, 0.35);
            backdrop-filter: blur(10px);
            text-align: center;
          }

          h1 {
            margin: 0 0 16px;
            font-size: clamp(1.8rem, 2.5vw, 2.4rem);
          }

          p {
            margin: 0;
            line-height: 1.6;
            color: rgba(244, 244, 244, 0.82);
          }
        `}</style>
      </main>
    );
  }

  return (
    <main className="configuration-page">
      <div className="panel">
        <h1>Configuración del Sistema</h1>
        
        {/* Tab Navigation */}
        <div className="tabs">
          <button 
            className={activeTab === "models" ? "active" : ""}
            onClick={() => setActiveTab("models")}
          >
            Modelos
          </button>
          <button 
            className={activeTab === "api" ? "active" : ""}
            onClick={() => setActiveTab("api")}
          >
            API
          </button>
          <button 
            className={activeTab === "external" ? "active" : ""}
            onClick={() => setActiveTab("external")}
          >
            APIs Externas
          </button>
          <button 
            className={activeTab === "system" ? "active" : ""}
            onClick={() => setActiveTab("system")}
          >
            Sistema
          </button>
          <button 
            className={activeTab === "history" ? "active" : ""}
            onClick={() => setActiveTab("history")}
          >
            Historial
          </button>
        </div>
        
        <form onSubmit={handleSubmit}>
          {/* Models Configuration */}
          {activeTab === "models" && config && (
            <div className="config-section">
              <h2>Configuración de Modelos</h2>
              {Object.entries(config.models).map(([modelName, modelConfig]) => (
                <div key={modelName} className="model-config">
                  <h3>Modelo: {modelName}</h3>
                  <div className="form-group">
                    <label>Proveedor:</label>
                    <input
                      type="text"
                      value={modelConfig.provider}
                      onChange={(e) => handleModelChange(modelName, "provider", e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>Nombre del Modelo:</label>
                    <input
                      type="text"
                      value={modelConfig.model_name}
                      onChange={(e) => handleModelChange(modelName, "model_name", e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>Temperatura:</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="2"
                      value={modelConfig.temperature}
                      onChange={(e) => handleModelChange(modelName, "temperature", parseFloat(e.target.value))}
                    />
                  </div>
                  <div className="form-group">
                    <label>Máx. Tokens:</label>
                    <input
                      type="number"
                      min="1"
                      max="4096"
                      value={modelConfig.max_tokens}
                      onChange={(e) => handleModelChange(modelName, "max_tokens", parseInt(e.target.value, 10))}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {/* API Configuration */}
          {activeTab === "api" && config && (
            <div className="config-section">
              <h2>Configuración de API</h2>
              <div className="form-group">
                <label>Host:</label>
                <input
                  type="text"
                  value={config.api.host}
                  onChange={(e) => handleAPIChange("host", e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Puerto:</label>
                <input
                  type="number"
                  value={config.api.port}
                  onChange={(e) => handleAPIChange("port", parseInt(e.target.value, 10))}
                />
              </div>
              <div className="form-group">
                <label>Debug:</label>
                <input
                  type="checkbox"
                  checked={config.api.debug}
                  onChange={(e) => handleAPIChange("debug", e.target.checked)}
                />
              </div>
            </div>
          )}
          
          {/* External APIs Configuration */}
          {activeTab === "external" && config && (
            <div className="config-section">
              <h2>APIs Externas</h2>
              <div className="form-group">
                <label>API Key de Materials Project:</label>
                <input
                  type="password"
                  value={config.external_apis.mp_api_key || ""}
                  onChange={(e) => handleExternalAPIChange("mp_api_key", e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>API Key de Semantic Scholar:</label>
                <input
                  type="password"
                  value={config.external_apis.semantic_scholar_api_key || ""}
                  onChange={(e) => handleExternalAPIChange("semantic_scholar_api_key", e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>API Key de OpenRouter:</label>
                <input
                  type="password"
                  value={config.external_apis.openrouter_api_key || ""}
                  onChange={(e) => handleExternalAPIChange("openrouter_api_key", e.target.value)}
                />
              </div>
            </div>
          )}
          
          {/* System Configuration */}
          {activeTab === "system" && config && (
            <div className="config-section">
              <h2>Configuración del Sistema</h2>
              <div className="form-group">
                <label>Nivel de Log:</label>
                <select
                  value={config.system.log_level}
                  onChange={(e) => handleSystemChange("log_level", e.target.value)}
                >
                  <option value="DEBUG">DEBUG</option>
                  <option value="INFO">INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                  <option value="CRITICAL">CRITICAL</option>
                </select>
              </div>
              <div className="form-group">
                <label>Directorio de Datos:</label>
                <input
                  type="text"
                  value={config.system.data_dir}
                  onChange={(e) => handleSystemChange("data_dir", e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Directorio Temporal:</label>
                <input
                  type="text"
                  value={config.system.temp_dir}
                  onChange={(e) => handleSystemChange("temp_dir", e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Timeout (segundos):</label>
                <input
                  type="number"
                  value={config.system.timeout}
                  onChange={(e) => handleSystemChange("timeout", parseInt(e.target.value, 10))}
                />
              </div>
            </div>
          )}
          
          {/* History View */}
          {activeTab === "history" && (
            <HistoryView />
          )}
          
          {/* Validation Results */}
          {validationResult && !validationResult.valid && (
            <div className="validation-errors">
              <h3>Errores de Validación</h3>
              <ul>
                {validationResult.errors?.map((error, index) => (
                  <li key={index}>{error.message || JSON.stringify(error)}</li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Action Buttons */}
          <div className="actions">
            <button 
              type="button" 
              onClick={handleValidate}
              disabled={validating || saving}
              className="validate-btn"
            >
              {validating ? "Validando..." : "Validar"}
            </button>
            <button 
              type="submit" 
              disabled={saving || validating}
              className="save-btn"
            >
              {saving ? "Guardando..." : "Aplicar"}
            </button>
          </div>
        </form>
      </div>
      
      <style jsx>{`
        .configuration-page {
          height: 100vh;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: clamp(24px, 6vw, 60px);
          background: radial-gradient(circle at top, rgba(109, 93, 252, 0.28), transparent 55%),
            radial-gradient(circle at bottom, rgba(80, 54, 239, 0.22), transparent 60%),
            #050505;
          color: #f4f4f4;
          overflow-y: auto;
        }

        .panel {
          max-width: 900px;
          width: 100%;
          background: rgba(12, 12, 12, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 24px;
          padding: clamp(24px, 4vw, 40px);
          box-shadow: 0 20px 55px rgba(0, 0, 0, 0.35);
          backdrop-filter: blur(10px);
        }

        h1 {
          margin: 0 0 16px;
          font-size: clamp(1.8rem, 2.5vw, 2.4rem);
          text-align: center;
        }

        .tabs {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }

        .tabs button {
          padding: 10px 20px;
          background: rgba(80, 54, 239, 0.3);
          border: 1px solid rgba(160, 140, 255, 0.32);
          border-radius: 8px;
          color: #f4f4f4;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .tabs button.active,
        .tabs button:hover {
          background: rgba(109, 93, 252, 0.52);
          border-color: rgba(255, 255, 255, 0.18);
        }

        .config-section {
          margin-bottom: 20px;
        }

        .model-config {
          background: rgba(20, 20, 30, 0.5);
          border-radius: 12px;
          padding: 15px;
          margin-bottom: 15px;
        }

        h2, h3 {
          margin: 0 0 15px 0;
          color: #a08cff;
        }

        h3 {
          margin-bottom: 10px;
        }

        .form-group {
          margin-bottom: 15px;
        }

        .form-group label {
          display: block;
          margin-bottom: 5px;
          font-weight: 500;
        }

        .form-group input, .form-group select {
          width: 100%;
          padding: 10px;
          background: rgba(30, 30, 40, 0.7);
          border: 1px solid rgba(160, 140, 255, 0.32);
          border-radius: 6px;
          color: #f4f4f4;
          font-size: 1rem;
        }

        .form-group input:focus, .form-group select:focus {
          outline: none;
          border-color: rgba(109, 93, 252, 0.82);
          box-shadow: 0 0 0 2px rgba(109, 93, 252, 0.32);
        }

        .validation-errors {
          background: rgba(200, 50, 50, 0.2);
          border: 1px solid rgba(255, 100, 100, 0.3);
          border-radius: 8px;
          padding: 15px;
          margin: 15px 0;
        }

        .validation-errors h3 {
          color: #ff8080;
          margin-top: 0;
        }

        .validation-errors ul {
          margin: 10px 0;
          padding-left: 20px;
        }

        .validation-errors li {
          margin-bottom: 5px;
          color: #ffaaaa;
        }

        .actions {
          display: flex;
          gap: 15px;
          justify-content: center;
          margin-top: 20px;
          flex-wrap: wrap;
        }

        .actions button {
          padding: 12px 24px;
          border-radius: 8px;
          border: none;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .validate-btn {
          background: rgba(80, 54, 239, 0.5);
          color: #f4f4f4;
        }

        .save-btn {
          background: linear-gradient(135deg, #6d5dfc, #5036ef);
          color: #f4f4f4;
        }

        .actions button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .actions button:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        @media (max-width: 768px) {
          .panel {
            padding: clamp(16px, 4vw, 24px);
          }
          
          .tabs {
            justify-content: center;
          }
        }
      `}</style>
    </main>
  );
}
