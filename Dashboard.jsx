/**
 * SewerSentinel Dashboard
 *
 * A production-grade infrastructure monitoring interface
 * Aesthetic: Industrial/Utilitarian with subtle engineering precision
 *
 * Features:
 * - File upload (drag-and-drop) for images and videos
 * - Real-time API integration with backend
 * - Falls back to mock data for demo purposes
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Mock data for demonstration (fallback when API unavailable)
const mockPipeData = [
  {
    id: 'PIPE-2847',
    location: 'Main St & 5th Ave',
    currentGrade: 4,
    predictedGrade6Mo: 5,
    riskScore: 87,
    daysToFailure: 145,
    defects: ['CC', 'I', 'JD'],
    lastInspected: '2026-01-15',
    material: 'Vitrified Clay',
    age: 47,
    costRepair: 12500,
    costEmergency: 89000
  },
  {
    id: 'PIPE-1923',
    location: 'Oak St (Near Elementary School)',
    currentGrade: 3,
    predictedGrade6Mo: 4,
    riskScore: 72,
    daysToFailure: 280,
    defects: ['CL', 'RF'],
    lastInspected: '2026-01-18',
    material: 'Concrete',
    age: 35,
    costRepair: 8200,
    costEmergency: 52000
  },
  {
    id: 'PIPE-3156',
    location: 'Industrial Blvd Sector 4',
    currentGrade: 5,
    predictedGrade6Mo: 5,
    riskScore: 95,
    daysToFailure: 45,
    defects: ['X', 'B', 'I'],
    lastInspected: '2026-01-20',
    material: 'Cast Iron',
    age: 62,
    costRepair: 28000,
    costEmergency: 175000
  },
  {
    id: 'PIPE-0891',
    location: 'Riverside Dr',
    currentGrade: 2,
    predictedGrade6Mo: 2,
    riskScore: 23,
    daysToFailure: null,
    defects: ['DS'],
    lastInspected: '2026-01-12',
    material: 'PVC',
    age: 12,
    costRepair: 2100,
    costEmergency: 15000
  }
];

const defectCodeNames = {
  'CL': 'Longitudinal Crack',
  'CC': 'Circumferential Crack',
  'CM': 'Multiple Cracks',
  'FC': 'Fracture',
  'B': 'Broken',
  'H': 'Hole',
  'X': 'Collapse',
  'RF': 'Root (Fine)',
  'RM': 'Root (Medium)',
  'RB': 'Root (Ball)',
  'I': 'Infiltration',
  'JD': 'Joint Displaced',
  'JS': 'Joint Separated',
  'DS': 'Deposits Settled',
  'DAG': 'Deposits Attached',
  'COR': 'Corrosion',
  'SD': 'Surface Damage'
};

// Grade color mapping
const getGradeColor = (grade) => {
  const colors = {
    1: '#22c55e', // Green
    2: '#84cc16', // Lime
    3: '#eab308', // Yellow
    4: '#f97316', // Orange
    5: '#ef4444'  // Red
  };
  return colors[grade] || '#6b7280';
};

const getRiskColor = (score) => {
  if (score >= 80) return '#ef4444';
  if (score >= 60) return '#f97316';
  if (score >= 40) return '#eab308';
  return '#22c55e';
};

// API Helper Functions
const apiCall = async (endpoint, options = {}) => {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API call failed: ${endpoint}`, error);
    throw error;
  }
};

const checkApiHealth = async () => {
  try {
    const health = await apiCall('/api/health');
    return health.api_key_configured;
  } catch {
    return false;
  }
};

const analyzeImage = async (file, pipeId, context = {}) => {
  const formData = new FormData();
  formData.append('file', file);
  if (pipeId) formData.append('pipe_id', pipeId);

  // Add context fields
  Object.entries(context).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      formData.append(key, value);
    }
  });

  return apiCall('/api/full-analysis', {
    method: 'POST',
    body: formData,
  });
};

const analyzeVideo = async (file, pipeId, framesPerSecond = 1.0) => {
  const formData = new FormData();
  formData.append('file', file);
  if (pipeId) formData.append('pipe_id', pipeId);
  formData.append('frames_per_second', framesPerSecond);

  return apiCall('/api/analyze-video', {
    method: 'POST',
    body: formData,
  });
};

// Components
const StatCard = ({ label, value, subtext, icon, color }) => (
  <div style={{
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    border: '1px solid #2d3748',
    borderRadius: '4px',
    padding: '20px',
    position: 'relative',
    overflow: 'hidden'
  }}>
    <div style={{
      position: 'absolute',
      top: '-20px',
      right: '-20px',
      fontSize: '80px',
      opacity: 0.05,
      color: color || '#fff'
    }}>
      {icon}
    </div>
    <div style={{
      fontSize: '12px',
      color: '#94a3b8',
      textTransform: 'uppercase',
      letterSpacing: '1px',
      marginBottom: '8px'
    }}>
      {label}
    </div>
    <div style={{
      fontSize: '36px',
      fontWeight: '700',
      color: color || '#fff',
      fontFamily: "'JetBrains Mono', monospace"
    }}>
      {value}
    </div>
    {subtext && (
      <div style={{
        fontSize: '13px',
        color: '#64748b',
        marginTop: '4px'
      }}>
        {subtext}
      </div>
    )}
  </div>
);

const PriorityBadge = ({ rank }) => (
  <div style={{
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '28px',
    height: '28px',
    borderRadius: '4px',
    background: rank === 1 ? '#ef4444' : rank === 2 ? '#f97316' : rank === 3 ? '#eab308' : '#3b82f6',
    color: '#fff',
    fontSize: '12px',
    fontWeight: '700',
    fontFamily: "'JetBrains Mono', monospace"
  }}>
    #{rank}
  </div>
);

const GradeBadge = ({ grade, size = 'normal' }) => (
  <div style={{
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: size === 'large' ? '48px' : '32px',
    height: size === 'large' ? '48px' : '32px',
    borderRadius: '4px',
    background: getGradeColor(grade),
    color: '#fff',
    fontSize: size === 'large' ? '20px' : '14px',
    fontWeight: '700',
    fontFamily: "'JetBrains Mono', monospace"
  }}>
    {grade}
  </div>
);

const RiskMeter = ({ score }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
    <div style={{
      flex: 1,
      height: '8px',
      background: '#1e293b',
      borderRadius: '4px',
      overflow: 'hidden'
    }}>
      <div style={{
        width: `${score}%`,
        height: '100%',
        background: `linear-gradient(90deg, #22c55e 0%, #eab308 50%, #ef4444 100%)`,
        borderRadius: '4px',
        transition: 'width 0.5s ease'
      }} />
    </div>
    <span style={{
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '14px',
      fontWeight: '600',
      color: getRiskColor(score),
      minWidth: '40px'
    }}>
      {score}%
    </span>
  </div>
);

const LoadingSpinner = ({ size = 24 }) => (
  <div style={{
    width: size,
    height: size,
    border: '3px solid #2d3748',
    borderTopColor: '#3b82f6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  }}>
    <style>{`
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
    `}</style>
  </div>
);

// File Upload Component with Drag & Drop
const FileUploader = ({ onUpload, isAnalyzing }) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      onUpload(files[0]);
    }
  }, [onUpload]);

  const handleFileSelect = (e) => {
    if (e.target.files.length > 0) {
      onUpload(e.target.files[0]);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => !isAnalyzing && fileInputRef.current?.click()}
      style={{
        border: `2px dashed ${isDragging ? '#3b82f6' : '#2d3748'}`,
        borderRadius: '8px',
        padding: '40px',
        textAlign: 'center',
        cursor: isAnalyzing ? 'wait' : 'pointer',
        background: isDragging ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
        transition: 'all 0.2s ease'
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,video/*"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
        disabled={isAnalyzing}
      />

      {isAnalyzing ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          <LoadingSpinner size={48} />
          <div style={{ color: '#94a3b8', fontSize: '14px' }}>
            Analyzing with Gemini 3...
          </div>
        </div>
      ) : (
        <>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>
            📁
          </div>
          <div style={{ color: '#e2e8f0', fontSize: '16px', marginBottom: '8px' }}>
            Drop an image or video here
          </div>
          <div style={{ color: '#64748b', fontSize: '13px' }}>
            or click to browse • Supports JPG, PNG, MP4, AVI
          </div>
        </>
      )}
    </div>
  );
};

// Analysis Modal
const AnalysisModal = ({ isOpen, onClose, onAnalyze, isAnalyzing }) => {
  const [context, setContext] = useState({
    pipe_age_years: '',
    pipe_material: 'concrete',
    pipe_diameter_inches: '',
    traffic_load: 'medium',
    location_type: 'residential'
  });

  if (!isOpen) return null;

  const handleUpload = async (file) => {
    await onAnalyze(file, context);
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.8)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: '#1a1a2e',
        borderRadius: '12px',
        padding: '32px',
        width: '600px',
        maxWidth: '90vw',
        maxHeight: '90vh',
        overflow: 'auto',
        border: '1px solid #2d3748'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '600' }}>
            Analyze New Inspection
          </h2>
          <button
            onClick={onClose}
            disabled={isAnalyzing}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              fontSize: '24px',
              cursor: 'pointer'
            }}
          >
            x
          </button>
        </div>

        <FileUploader onUpload={handleUpload} isAnalyzing={isAnalyzing} />

        <div style={{ marginTop: '24px' }}>
          <h3 style={{ fontSize: '14px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '16px' }}>
            Pipe Context (Optional)
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>
                Pipe Age (years)
              </label>
              <input
                type="number"
                value={context.pipe_age_years}
                onChange={(e) => setContext({ ...context, pipe_age_years: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  background: '#0f172a',
                  border: '1px solid #2d3748',
                  borderRadius: '4px',
                  color: '#e2e8f0',
                  fontSize: '14px'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>
                Material
              </label>
              <select
                value={context.pipe_material}
                onChange={(e) => setContext({ ...context, pipe_material: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  background: '#0f172a',
                  border: '1px solid #2d3748',
                  borderRadius: '4px',
                  color: '#e2e8f0',
                  fontSize: '14px'
                }}
              >
                <option value="concrete">Concrete</option>
                <option value="clay">Vitrified Clay</option>
                <option value="pvc">PVC</option>
                <option value="cast_iron">Cast Iron</option>
                <option value="hdpe">HDPE</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>
                Traffic Load Above
              </label>
              <select
                value={context.traffic_load}
                onChange={(e) => setContext({ ...context, traffic_load: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  background: '#0f172a',
                  border: '1px solid #2d3748',
                  borderRadius: '4px',
                  color: '#e2e8f0',
                  fontSize: '14px'
                }}
              >
                <option value="none">None</option>
                <option value="light">Light</option>
                <option value="medium">Medium</option>
                <option value="heavy">Heavy</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>
                Location Type
              </label>
              <select
                value={context.location_type}
                onChange={(e) => setContext({ ...context, location_type: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  background: '#0f172a',
                  border: '1px solid #2d3748',
                  borderRadius: '4px',
                  color: '#e2e8f0',
                  fontSize: '14px'
                }}
              >
                <option value="residential">Residential</option>
                <option value="commercial">Commercial</option>
                <option value="industrial">Industrial</option>
                <option value="school">Near School</option>
                <option value="hospital">Near Hospital</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Analysis Result Panel
const AnalysisResultPanel = ({ result, uploadedImage, onClose }) => {
  if (!result) return null;

  const defects = result.defects || [];
  const prediction = result.prediction || {};

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: '600' }}>
          Analysis Result
        </h2>
        <button
          onClick={onClose}
          style={{
            padding: '8px 16px',
            background: '#2d3748',
            border: 'none',
            borderRadius: '4px',
            color: '#e2e8f0',
            cursor: 'pointer'
          }}
        >
          Back to Queue
        </button>
      </div>

      {/* Uploaded Image Preview */}
      {uploadedImage && (
        <div style={{
          marginBottom: '24px',
          borderRadius: '8px',
          overflow: 'hidden',
          border: '1px solid #2d3748'
        }}>
          <img
            src={uploadedImage}
            alt="Uploaded inspection"
            style={{
              width: '100%',
              maxHeight: '300px',
              objectFit: 'contain',
              background: '#0f172a'
            }}
          />
        </div>
      )}

      {/* Summary */}
      <div style={{
        background: '#0f172a',
        border: '1px solid #2d3748',
        borderRadius: '8px',
        padding: '20px',
        marginBottom: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '18px', fontWeight: '600' }}>
            {result.pipe_id}
          </span>
          <GradeBadge grade={result.overall_grade} size="large" />
          <span style={{ color: '#64748b', fontSize: '14px' }}>
            Quick Rating: {result.quick_rating}
          </span>
        </div>

        {result.executive_summary && (
          <p style={{ color: '#94a3b8', fontSize: '14px', lineHeight: '1.6', margin: 0 }}>
            {result.executive_summary}
          </p>
        )}
      </div>

      {/* Detected Defects */}
      <div style={{
        background: '#0f172a',
        border: '1px solid #2d3748',
        borderRadius: '8px',
        padding: '20px',
        marginBottom: '20px'
      }}>
        <h3 style={{
          margin: '0 0 16px 0',
          fontSize: '14px',
          textTransform: 'uppercase',
          letterSpacing: '1px',
          color: '#94a3b8'
        }}>
          Detected Defects ({defects.length})
        </h3>

        {defects.length === 0 ? (
          <div style={{ color: '#22c55e', fontSize: '14px' }}>
            No significant defects detected
          </div>
        ) : (
          defects.map((defect, i) => (
            <div key={i} style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              padding: '12px',
              background: '#1a1a2e',
              borderRadius: '4px',
              marginBottom: '8px'
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '14px',
                    fontWeight: '600',
                    color: '#f97316'
                  }}>
                    {defect.defect_code}
                  </span>
                  <GradeBadge grade={defect.grade} />
                  <span style={{ color: '#e2e8f0', fontSize: '14px' }}>
                    {defect.defect_type || defectCodeNames[defect.defect_code] || 'Unknown'}
                  </span>
                </div>
                {defect.description && (
                  <span style={{ color: '#64748b', fontSize: '13px' }}>
                    {defect.description}
                  </span>
                )}
                <span style={{ color: '#4b5563', fontSize: '12px' }}>
                  Location: {defect.location_in_pipe} • Confidence: {Math.round((defect.confidence || 0) * 100)}%
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Prediction */}
      {prediction && prediction.failure_risk_score !== undefined && (
        <div style={{
          background: '#0f172a',
          border: '1px solid #2d3748',
          borderRadius: '8px',
          padding: '20px',
          marginBottom: '20px'
        }}>
          <h3 style={{
            margin: '0 0 16px 0',
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '1px',
            color: '#94a3b8'
          }}>
            Failure Prediction
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            <div>
              <div style={{ color: '#64748b', fontSize: '12px', marginBottom: '4px' }}>Risk Score</div>
              <div style={{
                fontSize: '32px',
                fontWeight: '700',
                color: getRiskColor(prediction.failure_risk_score),
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                {prediction.failure_risk_score}%
              </div>
            </div>

            {prediction.estimated_time_to_failure_months && (
              <div>
                <div style={{ color: '#64748b', fontSize: '12px', marginBottom: '4px' }}>Time to Failure</div>
                <div style={{
                  fontSize: '32px',
                  fontWeight: '700',
                  color: prediction.estimated_time_to_failure_months <= 12 ? '#ef4444' : '#eab308',
                  fontFamily: "'JetBrains Mono', monospace"
                }}>
                  {prediction.estimated_time_to_failure_months} mo
                </div>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
            <span style={{ color: '#64748b', fontSize: '13px' }}>Grade progression:</span>
            <GradeBadge grade={prediction.current_grade} />
            <span style={{ color: '#64748b' }}>→</span>
            <GradeBadge grade={prediction.predicted_grade_6_months} />
            <span style={{ color: '#64748b', fontSize: '13px' }}>(6 mo)</span>
            <span style={{ color: '#64748b' }}>→</span>
            <GradeBadge grade={prediction.predicted_grade_12_months} />
            <span style={{ color: '#64748b', fontSize: '13px' }}>(12 mo)</span>
          </div>

          {prediction.recommended_action && (
            <div style={{
              padding: '12px',
              background: '#1e3a5f',
              borderRadius: '4px',
              fontSize: '14px',
              color: '#93c5fd'
            }}>
              <strong>Recommendation:</strong> {prediction.recommended_action}
            </div>
          )}
        </div>
      )}

      {/* Cost Analysis */}
      {prediction && prediction.cost_estimate_repair > 0 && (
        <div style={{
          background: '#0f172a',
          border: '1px solid #2d3748',
          borderRadius: '8px',
          padding: '20px'
        }}>
          <h3 style={{
            margin: '0 0 16px 0',
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '1px',
            color: '#94a3b8'
          }}>
            Cost-Benefit Analysis
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{
              background: '#1a1a2e',
              padding: '16px',
              borderRadius: '4px',
              borderLeft: '3px solid #22c55e'
            }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                Proactive Repair
              </div>
              <div style={{
                fontSize: '24px',
                fontWeight: '700',
                color: '#22c55e',
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                ${prediction.cost_estimate_repair.toLocaleString()}
              </div>
            </div>
            <div style={{
              background: '#1a1a2e',
              padding: '16px',
              borderRadius: '4px',
              borderLeft: '3px solid #ef4444'
            }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                Emergency Cost
              </div>
              <div style={{
                fontSize: '24px',
                fontWeight: '700',
                color: '#ef4444',
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                ${prediction.cost_estimate_emergency.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const PipeCard = ({ pipe, rank, isSelected, onClick }) => (
  <div
    onClick={onClick}
    style={{
      background: isSelected
        ? 'linear-gradient(135deg, #1e3a5f 0%, #1a1a2e 100%)'
        : 'linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%)',
      border: isSelected ? '2px solid #3b82f6' : '1px solid #2d3748',
      borderRadius: '6px',
      padding: '16px',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      marginBottom: '12px'
    }}
  >
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
      <PriorityBadge rank={rank} />
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '14px',
            fontWeight: '600',
            color: '#e2e8f0'
          }}>
            {pipe.id}
          </span>
          <GradeBadge grade={pipe.currentGrade} />
          {pipe.currentGrade < pipe.predictedGrade6Mo && (
            <span style={{ color: '#f97316', fontSize: '12px' }}>
              → {pipe.predictedGrade6Mo}
            </span>
          )}
        </div>
        <div style={{
          fontSize: '13px',
          color: '#94a3b8',
          marginBottom: '8px'
        }}>
          {pipe.location}
        </div>
        <RiskMeter score={pipe.riskScore} />
        <div style={{
          display: 'flex',
          gap: '6px',
          marginTop: '10px',
          flexWrap: 'wrap'
        }}>
          {pipe.defects.map((code, i) => (
            <span key={i} style={{
              background: '#2d3748',
              padding: '2px 8px',
              borderRadius: '3px',
              fontSize: '11px',
              color: '#94a3b8',
              fontFamily: "'JetBrains Mono', monospace"
            }}>
              {code}
            </span>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const DetailPanel = ({ pipe }) => {
  if (!pipe) return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      color: '#64748b',
      fontSize: '14px'
    }}>
      Select a pipe to view details
    </div>
  );

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
          <h2 style={{
            margin: 0,
            fontSize: '24px',
            fontWeight: '700',
            color: '#e2e8f0',
            fontFamily: "'JetBrains Mono', monospace"
          }}>
            {pipe.id}
          </h2>
          <GradeBadge grade={pipe.currentGrade} size="large" />
        </div>
        <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px' }}>
          {pipe.location} {pipe.material && `• ${pipe.material}`} {pipe.age && `• ${pipe.age} years old`}
        </p>
      </div>

      {/* Risk Assessment */}
      <div style={{
        background: '#0f172a',
        border: '1px solid #2d3748',
        borderRadius: '6px',
        padding: '20px',
        marginBottom: '20px'
      }}>
        <h3 style={{
          margin: '0 0 16px 0',
          fontSize: '14px',
          textTransform: 'uppercase',
          letterSpacing: '1px',
          color: '#94a3b8'
        }}>
          Failure Risk Assessment
        </h3>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '20px'
        }}>
          <div style={{
            width: '100px',
            height: '100px',
            borderRadius: '50%',
            background: `conic-gradient(${getRiskColor(pipe.riskScore)} ${pipe.riskScore * 3.6}deg, #1e293b 0deg)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <div style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              background: '#0f172a',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column'
            }}>
              <span style={{
                fontSize: '28px',
                fontWeight: '700',
                color: getRiskColor(pipe.riskScore),
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                {pipe.riskScore}
              </span>
            </div>
          </div>
          <div style={{ flex: 1 }}>
            {pipe.daysToFailure ? (
              <>
                <div style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '4px' }}>
                  Estimated time to critical failure:
                </div>
                <div style={{
                  fontSize: '32px',
                  fontWeight: '700',
                  color: pipe.daysToFailure < 90 ? '#ef4444' : pipe.daysToFailure < 180 ? '#f97316' : '#eab308',
                  fontFamily: "'JetBrains Mono', monospace"
                }}>
                  {pipe.daysToFailure} days
                </div>
                <div style={{ fontSize: '13px', color: '#64748b' }}>
                  ~{Math.round(pipe.daysToFailure / 30)} months
                </div>
              </>
            ) : (
              <div style={{ fontSize: '14px', color: '#22c55e' }}>
                No imminent failure predicted
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Defects */}
      <div style={{
        background: '#0f172a',
        border: '1px solid #2d3748',
        borderRadius: '6px',
        padding: '20px',
        marginBottom: '20px'
      }}>
        <h3 style={{
          margin: '0 0 16px 0',
          fontSize: '14px',
          textTransform: 'uppercase',
          letterSpacing: '1px',
          color: '#94a3b8'
        }}>
          Detected Defects
        </h3>
        {pipe.defects.map((code, i) => (
          <div key={i} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '12px',
            background: '#1a1a2e',
            borderRadius: '4px',
            marginBottom: '8px'
          }}>
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '14px',
              fontWeight: '600',
              color: '#f97316',
              minWidth: '40px'
            }}>
              {code}
            </span>
            <span style={{ color: '#e2e8f0', fontSize: '14px' }}>
              {defectCodeNames[code] || 'Unknown Defect'}
            </span>
          </div>
        ))}
      </div>

      {/* Cost Analysis */}
      {pipe.costRepair && (
        <div style={{
          background: '#0f172a',
          border: '1px solid #2d3748',
          borderRadius: '6px',
          padding: '20px',
          marginBottom: '20px'
        }}>
          <h3 style={{
            margin: '0 0 16px 0',
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '1px',
            color: '#94a3b8'
          }}>
            Cost-Benefit Analysis
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{
              background: '#1a1a2e',
              padding: '16px',
              borderRadius: '4px',
              borderLeft: '3px solid #22c55e'
            }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                Proactive Repair Cost
              </div>
              <div style={{
                fontSize: '24px',
                fontWeight: '700',
                color: '#22c55e',
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                ${pipe.costRepair.toLocaleString()}
              </div>
            </div>
            <div style={{
              background: '#1a1a2e',
              padding: '16px',
              borderRadius: '4px',
              borderLeft: '3px solid #ef4444'
            }}>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '4px' }}>
                Emergency Failure Cost
              </div>
              <div style={{
                fontSize: '24px',
                fontWeight: '700',
                color: '#ef4444',
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                ${pipe.costEmergency.toLocaleString()}
              </div>
            </div>
          </div>
          <div style={{
            marginTop: '16px',
            padding: '12px',
            background: '#1e3a5f',
            borderRadius: '4px',
            fontSize: '14px',
            color: '#93c5fd'
          }}>
            Proactive repair saves <strong>${(pipe.costEmergency - pipe.costRepair).toLocaleString()}</strong> ({Math.round((1 - pipe.costRepair / pipe.costEmergency) * 100)}% savings)
          </div>
        </div>
      )}

      {/* Action Button */}
      <button style={{
        width: '100%',
        padding: '16px',
        background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
        border: 'none',
        borderRadius: '6px',
        color: '#fff',
        fontSize: '14px',
        fontWeight: '600',
        cursor: 'pointer',
        textTransform: 'uppercase',
        letterSpacing: '1px'
      }}>
        Generate PACP Report
      </button>
    </div>
  );
};

// Main Dashboard Component
export default function SewerSentinelDashboard() {
  const [selectedPipe, setSelectedPipe] = useState(null);
  const [pipes, setPipes] = useState(mockPipeData);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [apiAvailable, setApiAvailable] = useState(false);
  const [error, setError] = useState(null);
  const [showAnalysisView, setShowAnalysisView] = useState(false);

  // Check API availability on mount
  useEffect(() => {
    checkApiHealth().then(setApiAvailable).catch(() => setApiAvailable(false));
  }, []);

  // Handle file analysis
  const handleAnalyze = async (file, context) => {
    setIsAnalyzing(true);
    setError(null);

    // Create image preview
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setUploadedImage(e.target.result);
      reader.readAsDataURL(file);
    }

    try {
      let result;

      if (file.type.startsWith('video/')) {
        result = await analyzeVideo(file, null, 1.0);
      } else {
        result = await analyzeImage(file, null, context);
      }

      setAnalysisResult(result);
      setShowAnalysisView(true);
      setIsModalOpen(false);

      // Add to pipes list if it has prediction data
      if (result.prediction) {
        const newPipe = {
          id: result.pipe_id,
          location: 'New Analysis',
          currentGrade: result.overall_grade || 1,
          predictedGrade6Mo: result.prediction.predicted_grade_6_months || result.overall_grade,
          riskScore: result.prediction.failure_risk_score || 0,
          daysToFailure: result.prediction.estimated_time_to_failure_months
            ? result.prediction.estimated_time_to_failure_months * 30
            : null,
          defects: (result.defects || []).map(d => d.defect_code),
          lastInspected: new Date().toISOString().split('T')[0],
          material: context.pipe_material || 'Unknown',
          age: context.pipe_age_years || null,
          costRepair: result.prediction.cost_estimate_repair || 0,
          costEmergency: result.prediction.cost_estimate_emergency || 0
        };

        setPipes(prev => [newPipe, ...prev]);
      }

    } catch (err) {
      setError(err.message);
      console.error('Analysis failed:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Sort pipes by risk score
  const sortedPipes = [...pipes].sort((a, b) => b.riskScore - a.riskScore);

  // Calculate stats
  const criticalCount = pipes.filter(p => p.currentGrade >= 4).length;
  const totalRiskScore = pipes.length > 0
    ? Math.round(pipes.reduce((sum, p) => sum + p.riskScore, 0) / pipes.length)
    : 0;
  const totalSavings = pipes.reduce((sum, p) => sum + ((p.costEmergency || 0) - (p.costRepair || 0)), 0);

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0a0a0f',
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      color: '#e2e8f0'
    }}>
      {/* Add Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
      `}</style>

      {/* Header */}
      <header style={{
        background: 'linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%)',
        borderBottom: '1px solid #2d3748',
        padding: '16px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px'
          }}>
            🔍
          </div>
          <div>
            <h1 style={{
              margin: 0,
              fontSize: '20px',
              fontWeight: '700',
              letterSpacing: '-0.5px'
            }}>
              SewerSentinel
            </h1>
            <p style={{
              margin: 0,
              fontSize: '12px',
              color: '#64748b'
            }}>
              Autonomous Infrastructure Prediction System
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            background: '#1e293b',
            borderRadius: '6px',
            fontSize: '13px'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: apiAvailable ? '#22c55e' : '#f97316',
              animation: apiAvailable ? 'pulse 2s infinite' : 'none'
            }} />
            <style>{`
              @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
              }
            `}</style>
            {apiAvailable ? 'API Connected' : 'Demo Mode'}
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            style={{
              padding: '8px 20px',
              background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
              border: 'none',
              borderRadius: '6px',
              color: '#fff',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            + Analyze New
          </button>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div style={{
          padding: '12px 24px',
          background: '#7f1d1d',
          color: '#fecaca',
          fontSize: '14px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>Error: {error}</span>
          <button
            onClick={() => setError(null)}
            style={{ background: 'none', border: 'none', color: '#fecaca', cursor: 'pointer' }}
          >
            x
          </button>
        </div>
      )}

      {/* Stats Row */}
      <div style={{
        padding: '24px',
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '16px'
      }}>
        <StatCard
          label="Pipes Analyzed"
          value={pipes.length}
          subtext="In queue"
          icon="📊"
        />
        <StatCard
          label="Critical (Grade 4-5)"
          value={criticalCount}
          subtext="Require attention"
          icon="⚠️"
          color="#ef4444"
        />
        <StatCard
          label="Avg Risk Score"
          value={totalRiskScore}
          subtext="Network health"
          icon="📈"
          color={getRiskColor(totalRiskScore)}
        />
        <StatCard
          label="Potential Savings"
          value={`$${Math.round(totalSavings / 1000)}K`}
          subtext="vs. emergency repairs"
          icon="💰"
          color="#22c55e"
        />
      </div>

      {/* Main Content */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '400px 1fr',
        gap: '0',
        height: 'calc(100vh - 250px)'
      }}>
        {/* Priority Queue */}
        <div style={{
          borderRight: '1px solid #2d3748',
          padding: '0 24px 24px 24px',
          overflowY: 'auto'
        }}>
          <h2 style={{
            fontSize: '14px',
            textTransform: 'uppercase',
            letterSpacing: '1px',
            color: '#94a3b8',
            margin: '0 0 16px 0',
            padding: '16px 0',
            borderBottom: '1px solid #2d3748',
            position: 'sticky',
            top: 0,
            background: '#0a0a0f',
            zIndex: 10
          }}>
            Priority Repair Queue
          </h2>
          {sortedPipes.map((pipe, index) => (
            <PipeCard
              key={pipe.id}
              pipe={pipe}
              rank={index + 1}
              isSelected={selectedPipe?.id === pipe.id && !showAnalysisView}
              onClick={() => {
                setSelectedPipe(pipe);
                setShowAnalysisView(false);
              }}
            />
          ))}
        </div>

        {/* Detail Panel */}
        <div style={{
          background: '#0f0f1a',
          overflowY: 'auto'
        }}>
          {showAnalysisView && analysisResult ? (
            <AnalysisResultPanel
              result={analysisResult}
              uploadedImage={uploadedImage}
              onClose={() => setShowAnalysisView(false)}
            />
          ) : (
            <DetailPanel pipe={selectedPipe} />
          )}
        </div>
      </div>

      {/* Footer */}
      <footer style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '12px 24px',
        background: '#0a0a0f',
        borderTop: '1px solid #2d3748',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '12px',
        color: '#64748b'
      }}>
        <span>Powered by Gemini 3 • PACP Compliant</span>
        <span>Gemini 3 Hackathon 2026</span>
      </footer>

      {/* Analysis Modal */}
      <AnalysisModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onAnalyze={handleAnalyze}
        isAnalyzing={isAnalyzing}
      />
    </div>
  );
}
