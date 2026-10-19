import React from 'react';

/**
 * InsightsPanel - Displays AI-generated analysis summaries
 * Shows pipeline health, defect distribution, operational impact, and recommendations
 */
export default function InsightsPanel({ insights }) {
  if (!insights) return null;

  const {
    pipeline_health,
    defect_distribution,
    operational_impact,
    confidence_analysis,
    recommendations = []
  } = insights;

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(6,38,62,0.95) 0%, rgba(11,25,42,0.98) 100%)',
      border: '1px solid rgba(34,211,238,0.2)',
      borderRadius: 12,
      padding: 24,
      marginBottom: 24,
      boxShadow: '0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)'
    }}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <div style={{
          fontSize: 11,
          letterSpacing: 1.2,
          opacity: 0.5,
          textTransform: 'uppercase',
          marginBottom: 6
        }}>
          AI Analysis Summary
        </div>
        <h3 style={{
          fontSize: 18,
          fontWeight: 700,
          margin: 0,
          color: '#22d3ee'
        }}>
          Structural Assessment & Insights
        </h3>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        
        {/* Pipeline Health */}
        {pipeline_health && (
          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderLeft: `3px solid ${getStatusColor(pipeline_health.status)}`,
            borderRadius: 6,
            padding: 16
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{
                fontSize: 20,
                filter: 'grayscale(0.3)'
              }}>🔧</span>
              <div style={{ fontSize: 11, opacity: 0.5, letterSpacing: 1, textTransform: 'uppercase' }}>
                Pipeline Health
              </div>
            </div>
            <div style={{
              fontSize: 14,
              fontWeight: 700,
              color: getStatusColor(pipeline_health.status),
              marginBottom: 6
            }}>
              {pipeline_health.status}
            </div>
            <div style={{ fontSize: 12, lineHeight: 1.6, opacity: 0.85 }}>
              {pipeline_health.message}
            </div>
            <div style={{ fontSize: 10, opacity: 0.4, marginTop: 8 }}>
              Confidence: {pipeline_health.confidence}
            </div>
          </div>
        )}

        {/* Operational Impact */}
        {operational_impact && (
          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderLeft: `3px solid ${getUrgencyColor(operational_impact.urgency)}`,
            borderRadius: 6,
            padding: 16
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{ fontSize: 20 }}>⚡</span>
              <div style={{ fontSize: 11, opacity: 0.5, letterSpacing: 1, textTransform: 'uppercase' }}>
                Operational Impact
              </div>
            </div>
            <div style={{
              fontSize: 14,
              fontWeight: 700,
              color: getUrgencyColor(operational_impact.urgency),
              marginBottom: 6
            }}>
              {operational_impact.urgency} PRIORITY
            </div>
            <div style={{ fontSize: 12, lineHeight: 1.6, opacity: 0.85, marginBottom: 8 }}>
              {operational_impact.impact}
            </div>
            <div style={{
              display: 'inline-block',
              background: 'rgba(245,158,11,0.15)',
              border: '1px solid rgba(245,158,11,0.3)',
              borderRadius: 4,
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 600,
              color: '#f59e0b'
            }}>
              Timeline: {operational_impact.timeline}
            </div>
          </div>
        )}
      </div>

      {/* Defect Distribution */}
      {defect_distribution && defect_distribution.class_breakdown && (
        <div style={{
          background: 'rgba(0,0,0,0.2)',
          borderRadius: 6,
          padding: 16,
          marginBottom: 16
        }}>
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 12, opacity: 0.7 }}>
            📊 Defect Distribution
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.6, opacity: 0.85, marginBottom: 12 }}>
            {defect_distribution.message}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {Object.entries(defect_distribution.class_breakdown).map(([cls, count]) => (
              <span key={cls} style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                background: 'rgba(34,211,238,0.1)',
                border: '1px solid rgba(34,211,238,0.25)',
                borderRadius: 16,
                padding: '4px 12px',
                fontSize: 11,
                fontWeight: 600,
                color: '#22d3ee'
              }}>
                {cls}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Confidence Analysis */}
      {confidence_analysis && (
        <div style={{
          background: 'rgba(0,0,0,0.2)',
          borderRadius: 6,
          padding: 16,
          marginBottom: 16
        }}>
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, opacity: 0.7 }}>
            🎯 Detection Confidence: {confidence_analysis.average_confidence}% ({confidence_analysis.quality})
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.6, opacity: 0.85 }}>
            {confidence_analysis.message}
          </div>
          {confidence_analysis.manual_review_needed && (
            <div style={{
              marginTop: 10,
              padding: '8px 12px',
              background: 'rgba(251,191,36,0.1)',
              border: '1px solid rgba(251,191,36,0.3)',
              borderRadius: 6,
              fontSize: 11,
              color: '#fbbf24'
            }}>
              ⚠️ {confidence_analysis.manual_review_needed}
            </div>
          )}
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 12, opacity: 0.7 }}>
            💡 Recommended Actions
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {recommendations.map((rec, idx) => (
              <div key={idx} style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 12,
                background: 'rgba(0,0,0,0.2)',
                borderLeft: `3px solid ${getPriorityColor(rec.priority)}`,
                borderRadius: 6,
                padding: 12
              }}>
                <span style={{
                  display: 'inline-block',
                  background: getPriorityColor(rec.priority) + '22',
                  color: getPriorityColor(rec.priority),
                  borderRadius: 4,
                  padding: '3px 8px',
                  fontSize: 9,
                  fontWeight: 700,
                  letterSpacing: 0.5,
                  textTransform: 'uppercase',
                  flexShrink: 0
                }}>
                  {rec.priority}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                    {rec.action}
                  </div>
                  <div style={{ fontSize: 10, opacity: 0.5 }}>
                    {rec.timeline}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Helper functions for color coding
function getStatusColor(status) {
  const colors = {
    'HEALTHY': '#22c55e',
    'MINOR ISSUES': '#eab308',
    'ATTENTION NEEDED': '#f97316',
    'DEGRADED': '#ef4444',
    'CRITICAL': '#dc2626'
  };
  return colors[status] || '#94a3b8';
}

function getUrgencyColor(urgency) {
  const colors = {
    'LOW': '#22c55e',
    'MEDIUM': '#eab308',
    'HIGH': '#f97316',
    'IMMEDIATE': '#ef4444'
  };
  return colors[urgency] || '#94a3b8';
}

function getPriorityColor(priority) {
  const colors = {
    'ROUTINE': '#22c55e',
    'MEDIUM': '#eab308',
    'HIGH': '#f97316',
    'CRITICAL': '#ef4444'
  };
  return colors[priority] || '#94a3b8';
}
