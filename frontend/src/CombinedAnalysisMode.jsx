import React, { useState, useRef } from 'react';
import InsightsPanel from './InsightsPanel';

/**
 * CombinedAnalysisMode - Dual upload zones for sonar + underwater anomaly analysis
 */
export default function CombinedAnalysisMode({ API }) {
  const [sonarFiles, setSonarFiles] = useState([]);
  const [anomalyFiles, setAnomalyFiles] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [combinedResults, setCombinedResults] = useState(null);
  const [error, setError] = useState('');
  
  const sonarRef = useRef(null);
  const anomalyRef = useRef(null);

  const analyzeCombined = async () => {
    if (sonarFiles.length === 0 && anomalyFiles.length === 0) return;
    
    setIsAnalyzing(true);
    setError('');
    
    try {
      const formData = new FormData();
      sonarFiles.forEach(f => formData.append('sonar_files', f.file));
      anomalyFiles.forEach(f => formData.append('anomaly_files', f.file));
      formData.append('confidence_threshold', '0.25');
      
      const res = await fetch(`${API}/api/sonar/analyze-combined`, {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) throw new Error('Analysis failed');
      const data = await res.json();
      setCombinedResults(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const UploadZone = ({ title, files, setFiles, fileRef, color, icon }) => (
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color, display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 18 }}>{icon}</span>
        {title}
      </div>
      
      <div 
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = color; }}
        onDragLeave={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}
        onDrop={(e) => {
          e.preventDefault();
          e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
          const newFiles = Array.from(e.dataTransfer.files).map((f, i) => ({
            id: Date.now() + i,
            file: f,
            preview: URL.createObjectURL(f)
          }));
          setFiles(newFiles);
        }}
        style={{
          border: '2px dashed rgba(255,255,255,0.1)',
          borderRadius: 12,
          padding: 32,
          textAlign: 'center',
          cursor: 'pointer',
          background: 'rgba(0,0,0,0.2)',
          minHeight: 200
        }}
      >
        <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.4 }}>📁</div>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
          {files.length > 0 ? `${files.length} image(s) uploaded` : 'Drop images or click to browse'}
        </div>
        <div style={{ fontSize: 11, opacity: 0.5 }}>PNG, JPG, TIFF • Multiple upload</div>
        
        {files.length > 0 && (
          <div style={{ marginTop: 16, display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'center' }}>
            {files.slice(0, 4).map((f) => (
              <div key={f.id} style={{ width: 60, height: 60, borderRadius: 6, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.15)' }}>
                <img src={f.preview} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
            ))}
            {files.length > 4 && (
              <div style={{ width: 60, height: 60, borderRadius: 6, background: 'rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color }}>
                +{files.length - 4}
              </div>
            )}
          </div>
        )}
      </div>
      
      <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={(e) => {
        const newFiles = Array.from(e.target.files).map((f, i) => ({
          id: Date.now() + i,
          file: f,
          preview: URL.createObjectURL(f)
        }));
        setFiles(newFiles);
      }} />
    </div>
  );

  return (
    <div>
      <div className="card mb-20">
        <div style={{ marginBottom: 20 }}>
          <div className="card-title" style={{ marginBottom: 8 }}>Combined Analysis Mode</div>
          <p style={{ fontSize: 12, opacity: 0.6, lineHeight: 1.5 }}>
            Upload sonar images (SubPipe + Marine-PULSE) and underwater anomaly images (General Detection) for comprehensive dual-model analysis
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
          <UploadZone 
            title="Sonar Images (SSS/SAS)"
            files={sonarFiles}
            setFiles={setSonarFiles}
            fileRef={sonarRef}
            color="#22d3ee"
            icon="🔊"
          />
          
          <UploadZone 
            title="Underwater Anomaly Images"
            files={anomalyFiles}
            setFiles={setAnomalyFiles}
            fileRef={anomalyRef}
            color="#f59e0b"
            icon="🔍"
          />
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <button 
            className="btn btn-primary"
            disabled={sonarFiles.length === 0 && anomalyFiles.length === 0 || isAnalyzing}
            onClick={analyzeCombined}
          >
            {isAnalyzing && <span className="spinner" />}
            🚀 Analyze Combined
          </button>
          
          <div style={{ fontSize: 11, opacity: 0.5 }}>
            {sonarFiles.length > 0 && `${sonarFiles.length} sonar`}
            {sonarFiles.length > 0 && anomalyFiles.length > 0 && ' + '}
            {anomalyFiles.length > 0 && `${anomalyFiles.length} anomaly`}
          </div>
          
          {(sonarFiles.length > 0 || anomalyFiles.length > 0) && (
            <button className="btn btn-ghost" onClick={() => { setSonarFiles([]); setAnomalyFiles([]); }}>
              Clear All
            </button>
          )}
        </div>

        {error && (
          <div style={{ marginTop: 12, padding: 12, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 6, color: '#ef4444', fontSize: 12 }}>
            ⚠️ {error}
          </div>
        )}
      </div>

      {/* Combined Results Display */}
      {combinedResults && (
        <>
          {/* Insights Panels - Side by Side */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
            {combinedResults.sonar.insights && (
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 12, color: '#22d3ee' }}>
                  🔊 SONAR ANALYSIS INSIGHTS
                </div>
                <InsightsPanel insights={combinedResults.sonar.insights} />
              </div>
            )}
            
            {combinedResults.anomaly.insights && (
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 12, color: '#f59e0b' }}>
                  🔍 ANOMALY ANALYSIS INSIGHTS
                </div>
                <InsightsPanel insights={combinedResults.anomaly.insights} />
              </div>
            )}
          </div>

          {/* Summary Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
            <div className="card" style={{ textAlign: 'center', padding: '16px 10px' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#22d3ee' }}>
                {combinedResults.combined_summary.total_detections}
              </div>
              <div style={{ fontSize: 10, opacity: 0.45, marginTop: 4, textTransform: 'uppercase', letterSpacing: 1 }}>
                Total Detections
              </div>
            </div>
            
            <div className="card" style={{ textAlign: 'center', padding: '16px 10px' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#22d3ee' }}>
                {combinedResults.sonar.total_detections}
              </div>
              <div style={{ fontSize: 10, opacity: 0.45, marginTop: 4, textTransform: 'uppercase', letterSpacing: 1 }}>
                Sonar Detections
              </div>
            </div>
            
            <div className="card" style={{ textAlign: 'center', padding: '16px 10px' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#f59e0b' }}>
                {combinedResults.anomaly.total_detections}
              </div>
              <div style={{ fontSize: 10, opacity: 0.45, marginTop: 4, textTransform: 'uppercase', letterSpacing: 1 }}>
                Anomaly Detections
              </div>
            </div>
            
            <div className="card" style={{ textAlign: 'center', padding: '16px 10px' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#ef4444' }}>
                {combinedResults.combined_summary.total_critical}
              </div>
              <div style={{ fontSize: 10, opacity: 0.45, marginTop: 4, textTransform: 'uppercase', letterSpacing: 1 }}>
                Critical Issues
              </div>
            </div>
          </div>

          {/* Side-by-side detailed results */}
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>
            Detailed Analysis Comparison
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {/* Sonar Results */}
            <div className="card">
              <div className="card-title" style={{ color: '#22d3ee', marginBottom: 12 }}>
                🔊 Sonar Detection Results
              </div>
              {combinedResults.sonar.results.map((r, idx) => (
                <div key={idx} style={{ marginBottom: 16, padding: 12, background: 'rgba(34,211,238,0.05)', borderRadius: 6 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 8 }}>
                    {r.filename}
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>
                    {r.total_detections} detection{r.total_detections !== 1 && 's'} 
                    {r.critical_count > 0 && ` • ${r.critical_count} critical`}
                  </div>
                </div>
              ))}
            </div>

            {/* Anomaly Results */}
            <div className="card">
              <div className="card-title" style={{ color: '#f59e0b', marginBottom: 12 }}>
                🔍 Anomaly Detection Results
              </div>
              {combinedResults.anomaly.results.map((r, idx) => (
                <div key={idx} style={{ marginBottom: 16, padding: 12, background: 'rgba(245,158,11,0.05)', borderRadius: 6 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 8 }}>
                    {r.filename}
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>
                    {r.total_detections} detection{r.total_detections !== 1 && 's'} • Grade: {r.grade} • Risk: {r.risk_score}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
