import React, { useState, useEffect, useRef } from 'react';
import { 
  Leaf, 
  Cpu, 
  Compass, 
  Settings as SettingsIcon, 
  UploadCloud, 
  AlertTriangle, 
  CheckCircle, 
  Activity, 
  Info,
  Layers, 
  Gauge, 
  Globe, 
  Download,
  AlertOctagon,
  Play,
  Search,
  Code
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Cell
} from 'recharts';

import * as pdfjsLib from 'pdfjs-dist';
import mammoth from 'mammoth';

// API Configuration
const API_BASE_URL = 'http://localhost:8000';

type TabType = 'home' | 'analyze' | 'recommendations' | 'settings';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('home');
  const [zone, setZone] = useState<string>('IN');
  const [useGlobalAverage, setUseGlobalAverage] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [apiHealth, setApiHealth] = useState<'healthy' | 'offline' | 'mock'>('healthy');
  
  // Analysis Output
  const [result, setResult] = useState<any>(null);
  const [zonesList, setZonesList] = useState<any>([]);

  // Drag and drop / Paste / Extraction State
  const [dragActive, setDragActive] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [codeText, setCodeText] = useState<string>('');
  const [previewFilename, setPreviewFilename] = useState<string>('pasted_code.py');
  const [extractionLoading, setExtractionLoading] = useState<boolean>(false);

  // Settings State
  const [concurrencyLimit, setConcurrencyLimit] = useState<number>(10);
  const [maxNestingDepthThreshold, setMaxNestingDepthThreshold] = useState<number>(3);
  const [zoneQuery, setZoneQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchingZones, setSearchingZones] = useState<boolean>(false);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);

  // Fetch initial data (health & zones list)
  useEffect(() => {
    const fetchHealthAndZones = async () => {
      try {
        const healthRes = await fetch(`${API_BASE_URL}/health`);
        if (healthRes.ok) {
          const healthData = await healthRes.json();
          if (healthData.status === 'healthy') {
            setApiHealth('healthy');
          }
        } else {
          setApiHealth('mock');
        }
      } catch (err) {
        setApiHealth('mock');
      }

      try {
        const zonesRes = await fetch(`${API_BASE_URL}/zones`);
        if (zonesRes.ok) {
          const zonesData = await zonesRes.json();
          const zonesArr = Object.keys(zonesData).map(k => ({
            key: k,
            ...zonesData[k]
          }));
          setZonesList(zonesArr);
        } else {
          loadFallbackZones();
        }
      } catch (err) {
        loadFallbackZones();
      }
    };

    fetchHealthAndZones();
  }, []);

  const loadFallbackZones = () => {
    setZonesList([
      { key: 'IN', display_name: 'India National Grid', country_name: 'India', carbon_intensity: 435 },
      { key: 'DK-DK1', display_name: 'Denmark (West)', country_name: 'Denmark', carbon_intensity: 150 },
      { key: 'FR', display_name: 'France Grid', country_name: 'France', carbon_intensity: 50 },
      { key: 'US-NW', display_name: 'US Northwest Region', country_name: 'United States', carbon_intensity: 300 },
      { key: 'GLOBAL', display_name: 'Global Average Fallback', country_name: 'Global', carbon_intensity: 435 }
    ]);
  };

  // Search zones dynamically when query changes
  useEffect(() => {
    if (!zoneQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const delayDebounce = setTimeout(async () => {
      setSearchingZones(true);
      try {
        const res = await fetch(`${API_BASE_URL}/search-zones?q=${encodeURIComponent(zoneQuery)}`);
        if (res.ok) {
          const searchData = await res.json();
          const searchArr = Object.keys(searchData).map(k => ({
            key: k,
            ...searchData[k]
          }));
          setSearchResults(searchArr);
        } else {
          const filtered = zonesList.filter((z: any) => 
            z.display_name?.toLowerCase().includes(zoneQuery.toLowerCase()) ||
            z.key?.toLowerCase().includes(zoneQuery.toLowerCase()) ||
            z.country_name?.toLowerCase().includes(zoneQuery.toLowerCase())
          );
          setSearchResults(filtered);
        }
      } catch (err) {
        console.error("Zone search error:", err);
        const filtered = zonesList.filter((z: any) => 
          z.display_name?.toLowerCase().includes(zoneQuery.toLowerCase()) ||
          z.key?.toLowerCase().includes(zoneQuery.toLowerCase()) ||
          z.country_name?.toLowerCase().includes(zoneQuery.toLowerCase())
        );
        setSearchResults(filtered);
      } finally {
        setSearchingZones(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [zoneQuery, zonesList]);

  // Client-side text extraction from PDF
  const extractTextFromPdf = async (file: File): Promise<string> => {
    try {
      const arrayBuffer = await file.arrayBuffer();
      pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
      
      const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
      const pdf = await loadingTask.promise;
      let fullText = '';
      
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        const pageText = textContent.items
          .map((item: any) => item.str || '')
          .join(' ');
        fullText += pageText + '\n';
      }
      
      if (!fullText.trim()) {
        throw new Error("No readable text found in the PDF file.");
      }
      return fullText;
    } catch (err: any) {
      console.error("PDF Extraction error:", err);
      throw new Error(`PDF text extraction failed: ${err.message || 'Worker unreachable or blocked. You can paste the code directly instead.'}`);
    }
  };

  // Client-side text extraction from DOCX
  const extractTextFromDocx = async (file: File): Promise<string> => {
    try {
      const arrayBuffer = await file.arrayBuffer();
      const result = await mammoth.extractRawText({ arrayBuffer });
      if (!result.value || !result.value.trim()) {
        throw new Error("No readable text found in the Word document.");
      }
      return result.value;
    } catch (err: any) {
      console.error("DOCX Extraction error:", err);
      throw new Error(`Word document text extraction failed: ${err.message || err}`);
    }
  };

  // General handler for files
  const handleIncomingFile = async (incomingFile: File) => {
    setError(null);
    setExtractionLoading(true);
    try {
      let extractedText = '';
      const name = incomingFile.name.toLowerCase();
      
      if (name.endsWith('.pdf')) {
        extractedText = await extractTextFromPdf(incomingFile);
      } else if (name.endsWith('.docx')) {
        extractedText = await extractTextFromDocx(incomingFile);
      } else {
        extractedText = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = (e) => {
            const content = e.target?.result as string;
            const isBinary = /[\x00-\x08\x0E-\x1F\x7F]/.test(content);
            if (isBinary) {
              reject(new Error("Couldn't extract readable code from this file (file appears to be binary/unreadable as plain text)."));
            } else {
              resolve(content);
            }
          };
          reader.onerror = () => reject(new Error("Failed to read file contents."));
          reader.readAsText(incomingFile);
        });
      }
      
      if (!extractedText.trim()) {
        throw new Error("Extracted text is empty.");
      }
      
      let targetFilename = incomingFile.name;
      if (!targetFilename.endsWith('.py')) {
        const lastDotIndex = targetFilename.lastIndexOf('.');
        if (lastDotIndex > 0) {
          targetFilename = targetFilename.substring(0, lastDotIndex) + '.py';
        } else {
          targetFilename = targetFilename + '.py';
        }
      }
      
      setCodeText(extractedText);
      setPreviewFilename(targetFilename);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to process the uploaded file.");
    } finally {
      setExtractionLoading(false);
    }
  };

  // Drag and drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      await handleIncomingFile(droppedFile);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      await handleIncomingFile(selectedFile);
    }
  };

  // Handle direct clipboard paste
  const handlePaste = (e: React.ClipboardEvent) => {
    const targetTagName = (e.target as HTMLElement).tagName.toLowerCase();
    if (targetTagName === 'textarea' || targetTagName === 'input') {
      return;
    }
    
    e.preventDefault();
    const pastedText = e.clipboardData.getData('text');
    if (pastedText && pastedText.trim()) {
      setCodeText(pastedText);
      setPreviewFilename('pasted_code.py');
      setError(null);
    }
  };

  const triggerFileSelect = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Submit file/code for analysis
  const handleSubmitAnalysis = async () => {
    if (!codeText.trim()) {
      setError('Code input cannot be empty.');
      return;
    }
    setLoading(true);
    setError(null);

    const fileToUpload = new File([codeText], previewFilename || 'pasted_code.py', { type: 'text/plain' });
    const formData = new FormData();
    formData.append('file', fileToUpload);
    formData.append('zone', zone);
    formData.append('use_global_average', String(useGlobalAverage));

    try {
      const res = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errorText = await res.text();
        let errorMsg = 'Server returned an error';
        try {
          const errorJson = JSON.parse(errorText);
          errorMsg = errorJson.detail || errorMsg;
        } catch {
          errorMsg = errorText || errorMsg;
        }
        throw new Error(errorMsg);
      }

      const data = await res.json();
      setResult(data);
      setActiveTab('analyze');
    } catch (err: any) {
      console.error(err);
      setError(`Analysis failed: ${err.message || 'Make sure the FastAPI server is running at http://localhost:8000'}`);
    } finally {
      setLoading(false);
    }
  };



  const handleExportJson = () => {
    if (!result) return;
    const jsonStr = JSON.stringify(result, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `code_carbon_report_${result.filename.replace('.', '_')}.json`;
    link.click();
  };

  const getCarbonZoneComparisonData = () => {
    if (!result) return [];
    
    // Extract runtime energy (Joules)
    const energy_joules = result.pipeline_raw.energy_result.energy.energy_joules;
    const energy_kwh = energy_joules / 3600000;
    
    // Active zone info from result
    const activeZoneIntensity = result.pipeline_raw.carbon_result.carbon_data.carbon_intensity;
    const activeZoneKey = result.pipeline_raw.carbon_result.carbon_data.zone.zone_key;
    const activeZoneName = result.pipeline_raw.carbon_result.carbon_data.zone.display_name || activeZoneKey;
    
    // Define standard reference zones with known intensities
    const referenceZones = [
      { key: 'FR', display_name: 'France Grid (Clean)', carbon_intensity: 50 },
      { key: 'DK-DK1', display_name: 'Denmark West (Wind/Solar)', carbon_intensity: 150 },
      { key: 'US-NW', display_name: 'US Northwest Region', carbon_intensity: 300 },
      { key: 'GLOBAL', display_name: 'Global Average Fallback', carbon_intensity: 435 }
    ];
    
    // Check if the current selected zone matches any standard reference grid
    const allCompare = [...referenceZones];
    const exists = allCompare.some(z => z.key === activeZoneKey);
    
    if (!exists) {
      // Append the custom selected grid zone
      allCompare.push({
        key: activeZoneKey,
        display_name: `${activeZoneName} (Selected)`,
        carbon_intensity: activeZoneIntensity
      });
    } else {
      // Highlight the matching grid zone by renaming it
      const idx = allCompare.findIndex(z => z.key === activeZoneKey);
      allCompare[idx].carbon_intensity = activeZoneIntensity;
      allCompare[idx].display_name = `${allCompare[idx].display_name} (Selected)`;
    }
    
    // Sort compare list by intensity
    allCompare.sort((a, b) => a.carbon_intensity - b.carbon_intensity);
    
    return allCompare.map((z: any) => {
      const emissions_g = energy_kwh * z.carbon_intensity;
      return {
        key: z.key,
        name: z.display_name,
        intensity: z.carbon_intensity,
        emissions: parseFloat((emissions_g * 1000000).toFixed(4)) // Convert grams to micrograms (µg) for display scaling
      };
    });
  };

  const getComplexityMetricsData = () => {
    if (!result || !result.pipeline_raw.complexity_score) return [];
    const metrics = result.pipeline_raw.complexity_score.metrics;
    return [
      { name: 'Cyclomatic Complexity', value: parseFloat((metrics.cyclomatic_complexity * 100).toFixed(1)) },
      { name: 'Nesting Depth', value: parseFloat((metrics.max_nesting_depth * 100).toFixed(1)) },
      { name: 'Function Density', value: parseFloat((metrics.function_density * 100).toFixed(1)) },
      { name: 'Smell Score', value: parseFloat((metrics.energy_smell_score * 100).toFixed(1)) }
    ];
  };

  const getFuzzySmellDistributionData = () => {
    if (!result || !result.pipeline_raw.energy_smell_report.findings) return [];
    const counts: Record<string, number> = {};
    result.pipeline_raw.energy_smell_report.findings.forEach((f: any) => {
      counts[f.category] = (counts[f.category] || 0) + 1;
    });
    return Object.keys(counts).map(cat => ({
      name: cat.toUpperCase(),
      value: counts[cat]
    }));
  };

  const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#a855f7'];

  return (
    <div className="app-container" onPaste={handlePaste} style={{ position: 'relative', overflow: 'hidden' }}>
      {/* Ambient background glow lights */}
      <div className="glow-blob glow-1" />
      <div className="glow-blob glow-2" />
      <div className="glow-blob glow-3" />
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand-section">
          <div className="brand-icon">
            <Leaf size={20} color="#060606" fill="#060606" />
          </div>
          <h1 className="brand-title">Code-Carbon</h1>
        </div>

        <nav className="nav-links" role="tablist" aria-label="Dashboard views">
          <li 
            className={`nav-item ${activeTab === 'home' ? 'active' : ''}`}
            onClick={() => setActiveTab('home')}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setActiveTab('home'); }}
            tabIndex={0}
            role="tab"
            aria-selected={activeTab === 'home'}
          >
            <Compass /> Home Overview
          </li>
          <li 
            className={`nav-item ${activeTab === 'analyze' ? 'active' : ''}`}
            onClick={() => setActiveTab('analyze')}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setActiveTab('analyze'); }}
            tabIndex={0}
            role="tab"
            aria-selected={activeTab === 'analyze'}
          >
            <Gauge /> Analysis & Charts
          </li>
          <li 
            className={`nav-item ${activeTab === 'recommendations' ? 'active' : ''}`}
            onClick={() => setActiveTab('recommendations')}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setActiveTab('recommendations'); }}
            tabIndex={0}
            role="tab"
            aria-selected={activeTab === 'recommendations'}
          >
            <Layers /> Recommendations
          </li>
          <li 
            className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setActiveTab('settings'); }}
            tabIndex={0}
            role="tab"
            aria-selected={activeTab === 'settings'}
          >
            <SettingsIcon /> Settings Config
          </li>
        </nav>

        <div className="sidebar-footer">
          <div className="api-status">
            <span className={`status-dot ${apiHealth === 'healthy' ? '' : apiHealth === 'mock' ? 'mock' : 'offline'}`} />
            <span>
              API Server: {apiHealth === 'healthy' ? 'Online' : apiHealth === 'mock' ? 'Mock Fallback' : 'Offline'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content Workspace */}
      <main className="main-workspace">
        {/* Header */}
        <header className="header-container">
          <div>
            <h2 
              className="page-title"
              style={activeTab === 'home' ? {
                fontSize: '48px',
                fontWeight: 700,
                background: 'linear-gradient(135deg, #10b981 0%, #8b5cf6 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                display: 'inline-block',
                lineHeight: '1.2'
              } : {}}
            >
              {activeTab === 'home' && 'Green Software Architecture'}
              {activeTab === 'analyze' && 'Environmental Risk Profiler'}
              {activeTab === 'recommendations' && 'Prioritized Optimizations'}
              {activeTab === 'settings' && 'Dashboard Configuration'}
            </h2>
            <p 
              className="page-subtitle"
              style={activeTab === 'home' ? {
                fontSize: '16px',
                fontWeight: 400,
                color: '#94a3b8',
                marginTop: '0.5rem'
              } : {}}
            >
              {activeTab === 'home' && 'Sustainability-First Framework for Predictive Carbon-Aware Code'}
              {activeTab === 'analyze' && 'Real-time structural metrics and carbon estimates'}
              {activeTab === 'recommendations' && 'AI recommendations weighted by mathematical risk exposure'}
              {activeTab === 'settings' && 'Adjust local threshold weights and simulation parameters'}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            {result && (
              <button className="btn btn-secondary" onClick={handleExportJson}>
                <Download size={16} /> Export JSON
              </button>
            )}
            {activeTab !== 'home' && (
              <button className="btn btn-primary" onClick={() => setActiveTab('home')}>
                <Play size={16} fill="currentColor" /> Analyze Code
              </button>
            )}
          </div>
        </header>

        {/* Persistent Context Banner */}
        {result && (
          <div style={{
            background: 'hsla(var(--accent-green), 0.06)',
            border: '1px solid hsla(var(--accent-green), 0.15)',
            borderRadius: '10px',
            padding: '0.65rem 1.25rem',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.85rem',
            color: 'hsl(var(--text-secondary))',
            animation: 'fadeIn var(--transition-fast)',
            flexWrap: 'wrap',
            gap: '0.75rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'hsl(var(--accent-green))', boxShadow: '0 0 8px hsl(var(--accent-green))' }} />
                Active Context: <strong style={{ color: 'hsl(var(--text-primary))' }}>{result.filename}</strong>
              </span>
              <span style={{ color: 'hsl(var(--border-color))' }}>|</span>
              <span>
                Grid: <strong style={{ color: 'hsl(var(--accent-green))' }}>{result.pipeline_raw.carbon_result.carbon_data.zone.display_name} ({result.pipeline_raw.carbon_result.carbon_data.zone.zone_key})</strong>
              </span>
              <span style={{ color: 'hsl(var(--border-color))' }}>|</span>
              <span>
                ESS Score: <strong style={{ color: 'hsl(var(--accent-orange))' }}>{result.research_metrics.energy_smell_score.toFixed(2)}/10</strong>
              </span>
              <span style={{ color: 'hsl(var(--border-color))' }}>|</span>
              <span>
                CIRS Risk: <strong style={{ color: 'hsl(var(--accent-purple))' }}>{result.research_metrics.carbon_impact_risk_score.toFixed(4)} e-gCO₂</strong>
              </span>
            </div>
            
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                className={`btn ${activeTab === 'analyze' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', height: 'auto', borderRadius: '6px' }}
                onClick={() => setActiveTab('analyze')}
              >
                View Charts
              </button>
              <button 
                className={`btn ${activeTab === 'recommendations' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', height: 'auto', borderRadius: '6px' }}
                onClick={() => setActiveTab('recommendations')}
              >
                View Recommendations ({result.recommendations.recommendations.length})
              </button>
            </div>
          </div>
        )}

        {error && (
          <div style={{
            background: 'hsla(350, 80%, 55%, 0.1)',
            border: '1px solid hsla(350, 80%, 55%, 0.3)',
            borderRadius: '10px',
            color: 'hsl(350, 80%, 65%)',
            padding: '1rem',
            marginBottom: '2rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem'
          }}>
            <AlertTriangle size={18} />
            <span style={{ fontSize: '0.9rem', fontWeight: 500, flex: 1 }}>{error}</span>
            <button 
              className="btn btn-secondary" 
              style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem', height: 'fit-content' }}
              onClick={() => setError(null)}
            >
              Clear
            </button>
          </div>
        )}

        {/* HOME VIEW */}
        {activeTab === 'home' && (
          <div className="view-wrapper" style={{ animation: 'slideUp var(--transition-slow)' }}>
            <div className="section-card" style={{ marginBottom: '2rem' }}>
              <h3 className="section-title" style={{ borderBottom: '1px solid hsl(var(--border-color))', paddingBottom: '0.75rem', marginBottom: '1.5rem' }}>
                <UploadCloud size={20} color="hsl(var(--accent-green))" style={{ marginRight: '0.5rem' }} /> 
                Code Analysis Input Portal
              </h3>
              
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '1.5rem',
                marginBottom: '1.5rem'
              }}>
                {/* Left Panel: Drag & Drop */}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <label style={{ fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', fontWeight: 600, marginBottom: '0.5rem' }}>
                    Option A: Drag & Drop File
                  </label>
                  <div 
                    className={`upload-container ${dragActive ? 'drag-active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    onClick={triggerFileSelect}
                    style={{
                      border: '2px dashed hsl(var(--border-color))',
                      borderRadius: '12px',
                      padding: '2.5rem 1.5rem',
                      textAlign: 'center',
                      cursor: 'pointer',
                      background: 'hsla(var(--bg-card), 0.3)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center',
                      alignItems: 'center',
                      flex: 1,
                      minHeight: '220px',
                      transition: 'var(--transition-normal)'
                    }}
                  >
                    <input 
                      type="file" 
                      ref={fileInputRef} 
                      style={{ display: 'none' }} 
                      accept=".py,.txt,.pdf,.docx"
                      onChange={handleFileChange}
                    />
                    <div className="upload-icon-wrapper" style={{ marginBottom: '1rem' }}>
                      <UploadCloud size={24} />
                    </div>
                    <p className="upload-title" style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                      Click to Browse or Drag File Here
                    </p>
                    <p className="upload-description" style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))' }}>
                      Supports Python (.py), text (.txt), PDF (.pdf), and Word (.docx)
                    </p>
                  </div>
                </div>

                {/* Right Panel: Direct Paste Code */}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <label style={{ fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', fontWeight: 600, marginBottom: '0.5rem' }}>
                    Option B: Paste Code Directly
                  </label>
                  <textarea
                    value={codeText}
                    onChange={(e) => setCodeText(e.target.value)}
                    placeholder="# Paste your Python script or text code here...&#10;# E.g.&#10;def run():&#10;    for i in range(10):&#10;        print(i)"
                    style={{
                      fontFamily: 'Fira Code, SFMono-Regular, Consolas, Monaco, monospace',
                      fontSize: '0.85rem',
                      lineHeight: '1.5',
                      padding: '1rem',
                      backgroundColor: '#070a0e',
                      color: '#c9d1d9',
                      border: '1px solid hsl(var(--border-color))',
                      borderRadius: '12px',
                      minHeight: '220px',
                      flex: 1,
                      outline: 'none',
                      resize: 'vertical'
                    }}
                  />
                </div>
              </div>

              {/* Extraction / Reading State indicator */}
              {extractionLoading && (
                <div style={{
                  background: 'hsla(var(--accent-blue), 0.05)',
                  border: '1px solid hsla(var(--accent-blue), 0.15)',
                  borderRadius: '10px',
                  padding: '1rem',
                  marginBottom: '1.5rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem'
                }}>
                  <div style={{
                    width: '16px',
                    height: '16px',
                    border: '2px solid hsl(var(--border-color))',
                    borderTopColor: 'hsl(var(--accent-blue))',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }} />
                  <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'hsl(var(--text-secondary))' }}>
                    Parsing document content client-side...
                  </span>
                </div>
              )}

              {/* Submission Controls */}
              <div style={{
                borderTop: '1px solid hsl(var(--border-color))',
                paddingTop: '1.5rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem'
              }}>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', flex: 1 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'hsl(var(--text-muted))', fontWeight: 600, marginBottom: '0.25rem' }}>
                      TARGET FILENAME
                    </label>
                    <input 
                      type="text" 
                      className="custom-input"
                      value={previewFilename}
                      onChange={(e) => setPreviewFilename(e.target.value)}
                      aria-label="Target Filename"
                      style={{
                        padding: '0.4rem 0.75rem',
                        fontSize: '0.85rem',
                        width: '180px'
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.75rem', color: 'hsl(var(--text-muted))', fontWeight: 600, marginBottom: '0.25rem' }}>
                      ANALYSIS GRID ZONE
                    </label>
                    <select 
                      className="custom-select" 
                      value={zone}
                      onChange={(e) => setZone(e.target.value)}
                      aria-label="Analysis Grid Zone"
                      style={{
                        height: '34px',
                        padding: '0 0.5rem',
                        fontSize: '0.85rem'
                      }}
                    >
                      {zonesList.map((z: any) => (
                        <option key={z.key} value={z.key}>
                          {z.display_name || z.key} ({z.carbon_intensity} gCO₂/kWh)
                        </option>
                      ))}
                    </select>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', cursor: 'pointer', marginTop: '1.25rem' }}>
                      <input 
                        type="checkbox" 
                        checked={useGlobalAverage} 
                        onChange={(e) => setUseGlobalAverage(e.target.checked)}
                        aria-label="Force Global Average grid fallback"
                        style={{ width: '14px', height: '14px', accentColor: 'hsl(var(--accent-green))' }}
                      />
                      <span>Force Global Average grid fallback</span>
                    </label>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
                  {codeText && (
                    <button 
                      className="btn btn-secondary" 
                      onClick={() => {
                        setCodeText('');
                        setPreviewFilename('pasted_code.py');
                      }}
                      style={{ borderRadius: '8px', padding: '0.5rem 1rem' }}
                    >
                      Clear Input
                    </button>
                  )}
                  <button 
                    className="btn btn-primary" 
                    onClick={handleSubmitAnalysis} 
                    disabled={loading || !codeText.trim()}
                    style={{ 
                      borderRadius: '8px', 
                      padding: '0.5rem 1.25rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    {loading ? (
                      <>
                        <div style={{
                          width: '14px',
                          height: '14px',
                          border: '2px solid transparent',
                          borderTopColor: 'currentColor',
                          borderRadius: '50%',
                          animation: 'spin 0.8s linear infinite'
                        }} />
                        <span>Running Analysis...</span>
                      </>
                    ) : (
                      <>
                        <Play size={14} fill="currentColor" />
                        <span>Run Predictive Analysis</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* How It Works Section */}
            <div style={{
              marginTop: '3rem',
              borderTop: '1px solid hsl(var(--border-color))',
              paddingTop: '2.5rem',
              animation: 'slideUp var(--transition-slow)'
            }}>
              <h4 style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.1rem',
                fontWeight: 600,
                textAlign: 'center',
                color: 'hsl(var(--text-secondary))',
                marginBottom: '2rem',
                letterSpacing: '0.5px',
                textTransform: 'uppercase'
              }}>
                How Code-Carbon Works
              </h4>
              
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1.5rem'
              }}>
                <div style={{
                  background: 'hsl(var(--bg-card))',
                  border: '1px solid hsl(var(--border-color))',
                  borderRadius: '12px',
                  padding: '1.25rem',
                  textAlign: 'center'
                }} className="how-it-works-card">
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: 'hsla(var(--accent-blue), 0.1)',
                    color: 'hsl(var(--accent-blue))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 1rem'
                  }}>
                    <UploadCloud size={20} />
                  </div>
                  <h5 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.25rem' }}>1. Load Code</h5>
                  <p style={{ fontSize: '0.75rem', color: 'hsl(var(--text-secondary))' }}>
                    Upload files (.py, .pdf, .docx) or paste code directly into the editor.
                  </p>
                </div>

                <div style={{
                  background: 'hsl(var(--bg-card))',
                  border: '1px solid hsl(var(--border-color))',
                  borderRadius: '12px',
                  padding: '1.25rem',
                  textAlign: 'center'
                }} className="how-it-works-card">
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: 'hsla(var(--accent-purple), 0.1)',
                    color: 'hsl(var(--accent-purple))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 1rem'
                  }}>
                    <Cpu size={20} />
                  </div>
                  <h5 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.25rem' }}>2. AST Static Analysis</h5>
                  <p style={{ fontSize: '0.75rem', color: 'hsl(var(--text-secondary))' }}>
                    Static analyzer maps structure against 12 key software energy rules.
                  </p>
                </div>

                <div style={{
                  background: 'hsl(var(--bg-card))',
                  border: '1px solid hsl(var(--border-color))',
                  borderRadius: '12px',
                  padding: '1.25rem',
                  textAlign: 'center'
                }} className="how-it-works-card">
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: 'hsla(var(--accent-green), 0.1)',
                    color: 'hsl(var(--accent-green))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 1rem'
                  }}>
                    <Globe size={20} />
                  </div>
                  <h5 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.25rem' }}>3. Carbon Calculation</h5>
                  <p style={{ fontSize: '0.75rem', color: 'hsl(var(--text-secondary))' }}>
                    Predicts run energy and emissions using live regional grid carbon metrics.
                  </p>
                </div>

                <div style={{
                  background: 'hsl(var(--bg-card))',
                  border: '1px solid hsl(var(--border-color))',
                  borderRadius: '12px',
                  padding: '1.25rem',
                  textAlign: 'center'
                }} className="how-it-works-card">
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: 'hsla(var(--accent-orange), 0.1)',
                    color: 'hsl(var(--accent-orange))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 1rem'
                  }}>
                    <CheckCircle size={20} />
                  </div>
                  <h5 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.25rem' }}>4. Prioritized Actions</h5>
                  <p style={{ fontSize: '0.75rem', color: 'hsl(var(--text-secondary))' }}>
                    Generates refactoring recommendations weighted by carbon impact risk.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ANALYZE VIEW */}
        {activeTab === 'analyze' && (
          <div className="view-wrapper">
            {loading && (
              <div className="section-card" style={{ textAlign: 'center', padding: '5rem 2rem' }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  border: '4px solid hsl(var(--border-color))',
                  borderTopColor: 'hsl(var(--accent-green))',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                  margin: '0 auto 2rem'
                }} />
                <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.35rem', marginBottom: '0.5rem' }}>
                  Analyzing Code Geometry...
                </h4>
                <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.9rem' }}>
                  Extracting AST symbols, computing cyclomatic metrics, and simulating carbon risk hazard indices.
                </p>
              </div>
            )}

            {!loading && !result && (
              <div className="section-card" style={{ textAlign: 'center', padding: '5rem 2rem' }}>
                <UploadCloud size={40} style={{ color: 'hsl(var(--text-muted))', marginBottom: '1.5rem' }} />
                <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', marginBottom: '0.5rem' }}>
                  No Code Analysis Loaded
                </h4>
                <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                  Please paste code or upload a file on the **Home Overview** page to begin the predictive green profiling.
                </p>
                <button className="btn btn-primary" onClick={() => setActiveTab('home')}>
                  Go to Home Overview
                </button>
              </div>
            )}

            {result && !loading && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                  <div>
                    <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 600 }}>
                      Analysis Report: {result.filename}
                    </h3>
                    <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.85rem' }}>
                      Processed at {new Date(result.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <button className="btn btn-secondary" onClick={() => setActiveTab('home')}>
                    Analyze Another Code / File
                  </button>
                </div>

                {/* Key Research Metrics Cards - Layer 1 (Primary Dashboard Overview) */}
                <div className="grid-cards">
                  {/* Primary Energy Card */}
                  <div className="stat-card green animate-stagger" style={{ animationDelay: '50ms' }}>
                    <div className="card-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      Estimated Run Energy
                      <span 
                        title="Estimated Run Energy (Joules): predicted energy drawn during runtime based on RAPL power models and control flow complexity."
                        style={{ cursor: 'help', color: '#94a3b8', display: 'inline-flex', alignItems: 'center' }}
                      >
                        <Info size={14} />
                      </span>
                    </div>
                    <div className="card-value">
                      {result.pipeline_raw.energy_result.energy.energy_joules.toFixed(3)}
                      <span className="card-unit">J</span>
                    </div>
                    <div className="card-trend">
                      <Activity size={14} color="#10b981" /> RAPL CPU Estimate
                    </div>
                  </div>

                  {/* Primary Carbon Card */}
                  <div className="stat-card blue animate-stagger" style={{ animationDelay: '100ms' }}>
                    <div className="card-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      Estimated Carbon Footprint
                      <span 
                        title="Carbon Impact Risk Score (e-gCO₂): predicted carbon risk computed by scaling code complexity metrics against grid carbon intensity."
                        style={{ cursor: 'help', color: '#94a3b8', display: 'inline-flex', alignItems: 'center' }}
                      >
                        <Info size={14} />
                      </span>
                    </div>
                    <div className="card-value">
                      {result.research_metrics.carbon_impact_risk_score.toFixed(4)}
                      <span className="card-unit">e-gCO₂</span>
                    </div>
                    <div className="card-trend">
                      <Globe size={14} color="#3b82f6" /> Carbon Risk Exposure
                    </div>
                  </div>

                  {/* Primary Risk Card */}
                  <div className="stat-card purple animate-stagger" style={{ animationDelay: '150ms' }}>
                    <div className="card-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      Structural Risk Assessment
                      <span 
                        title="Structural Complexity Index: AST complexity score based on nesting depth, loop structures, and conditional branching complexity."
                        style={{ cursor: 'help', color: '#94a3b8', display: 'inline-flex', alignItems: 'center' }}
                      >
                        <Info size={14} />
                      </span>
                    </div>
                    <div className="card-value" style={{ textTransform: 'capitalize' }}>
                      {result.pipeline_raw.complexity_score.risk_level.toLowerCase()}
                    </div>
                    <div className="card-trend">
                      <Layers size={14} color="#8b5cf6" /> Complexity Index ({result.pipeline_raw.complexity_score.structural_complexity_index.toFixed(3)})
                    </div>
                  </div>
                </div>

                {/* Collapsible Layer 2: Supporting Research & Versioning Metrics */}
                <div className="animate-stagger" style={{ animationDelay: '200ms', marginBottom: '2rem' }}>
                  <button
                    onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                    aria-expanded={showTechnicalDetails}
                    aria-controls="technical-details-panel"
                    className="btn btn-secondary"
                    style={{ width: '100%', justifyContent: 'center', padding: '0.6rem' }}
                  >
                    {showTechnicalDetails ? 'Hide Supporting Research & Versioning Metrics' : 'Show Supporting Research & Versioning Metrics'}
                  </button>

                  {showTechnicalDetails && (
                    <div 
                      id="technical-details-panel"
                      className="section-card" 
                      style={{ 
                        marginTop: '1rem', 
                        marginBottom: 0,
                        padding: '1.5rem',
                        background: 'rgba(255, 255, 255, 0.015)',
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                        gap: '1.5rem'
                      }}
                    >
                      <div>
                        <h4 style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.5rem' }}>Research Smell Score (ESS)</h4>
                        <p style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{result.research_metrics.energy_smell_score.toFixed(3)} <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>/ 10</span></p>
                        <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>Fuzzy Aggregation Version: v{result.research_metrics.ess_version}</p>
                      </div>
                      <div>
                        <h4 style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.5rem' }}>CIRS Model Version</h4>
                        <p style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>v{result.research_metrics.cirs_version}</p>
                        <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>Calculated using {zone} zone intensity profile.</p>
                      </div>
                      <div>
                        <h4 style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.5rem' }}>AST Line Count</h4>
                        <p style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{result.pipeline_raw.complexity_score.loc_raw} lines</p>
                        <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>Excludes comments and blank spacing blocks.</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Prototype Disclaimer Banner */}
                <div 
                  className="animate-stagger"
                  style={{
                    background: 'hsla(265, 80%, 65%, 0.08)',
                    border: '1px solid hsla(265, 80%, 65%, 0.2)',
                    borderRadius: '12px',
                    padding: '1rem 1.25rem',
                    marginBottom: '2rem',
                    fontSize: '0.85rem',
                    color: 'hsl(var(--text-secondary))',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    animationDelay: '250ms'
                  }}
                >
                  <AlertOctagon size={18} color="hsl(var(--accent-purple))" />
                  <span>
                    <strong>Prototype Notice:</strong> ESS and CIRS are experimental research-prototype models (version 1.0.0-prototype) intended to represent mathematical threat models rather than direct physical energy readings.
                  </span>
                </div>

                {/* Charts Area */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                  <div className="section-card animate-stagger" style={{ animationDelay: '300ms' }}>
                    <h4 className="section-title">
                      <Globe size={18} color="hsl(var(--accent-green))" /> Regional Grid Intensity Comparison
                    </h4>
                    <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
                      Shows estimated run carbon emissions (micro-grams of CO₂eq) based on grid intensities.
                    </p>
                    <div style={{ height: '280px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={getCarbonZoneComparisonData()}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#2a303c" />
                          <XAxis dataKey="name" stroke="#9ca3af" fontSize={11} tickFormatter={(t) => t.split(' ')[0]} />
                          <YAxis stroke="#9ca3af" fontSize={11} label={{ value: 'Emissions (µg)', angle: -90, position: 'insideLeft', fill: '#9ca3af' }} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
                            itemStyle={{ color: '#10b981' }}
                          />
                          <Bar dataKey="emissions" fill="hsl(var(--accent-green))">
                            {getCarbonZoneComparisonData().map((entry: any, index: number) => {
                              const activeZoneObj = zonesList.find((z: any) => z.key === zone);
                              const displayName = activeZoneObj?.display_name || zone;
                              const isCurrent = entry.name === displayName || entry.name.includes(zone);
                              return (
                                <Cell 
                                  key={`cell-${index}`} 
                                  fill={isCurrent ? 'hsl(var(--accent-orange))' : 'hsl(var(--accent-green))'} 
                                />
                              );
                            })}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="section-card animate-stagger" style={{ animationDelay: '350ms' }}>
                    <h4 className="section-title">
                      <Gauge size={18} color="hsl(var(--accent-purple))" /> Normalized Complexity Profile
                    </h4>
                    <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
                      Normalized structural complexity dimensions scaled on a standard [0, 100]% bounds.
                    </p>
                    <div style={{ height: '280px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={getComplexityMetricsData()} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke="#2a303c" />
                          <XAxis type="number" domain={[0, 100]} stroke="#9ca3af" fontSize={11} />
                          <YAxis dataKey="name" type="category" stroke="#9ca3af" fontSize={11} width={130} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#fff' }}
                            formatter={(value) => [`${value}%`, 'Value']}
                          />
                          <Bar dataKey="value" fill="hsl(var(--accent-purple))">
                            {getComplexityMetricsData().map((_entry, index) => (
                              <Cell 
                                key={`cell-${index}`} 
                                fill={PIE_COLORS[index % PIE_COLORS.length]} 
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* Raw metrics and smell breakdowns */}
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '1.5rem', marginBottom: '2rem' }}>
                  {/* Detailed metrics table */}
                  <div className="section-card animate-stagger" style={{ animationDelay: '400ms' }}>
                    <h4 className="section-title">
                      <Layers size={18} color="hsl(var(--accent-blue))" /> Software Structural Metrics
                    </h4>
                    <div className="data-table-wrapper" style={{ overflowX: 'auto' }}>
                      <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid hsl(var(--border-color))', textAlign: 'left' }}>
                            <th style={{ padding: '0.75rem 0.5rem', color: 'hsl(var(--text-muted))' }}>Metric</th>
                            <th style={{ padding: '0.75rem 0.5rem', color: 'hsl(var(--text-muted))', textAlign: 'right' }}>Raw Value</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr style={{ borderBottom: '1px solid hsla(var(--border-color), 0.5)' }}>
                            <td style={{ padding: '0.75rem 0.5rem' }}>Lines of Code (LOC)</td>
                            <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontWeight: 600 }}>
                              {result.pipeline_raw.complexity_metrics.lines_of_code}
                            </td>
                          </tr>
                          <tr style={{ borderBottom: '1px solid hsla(var(--border-color), 0.5)' }}>
                            <td style={{ padding: '0.75rem 0.5rem' }}>Cyclomatic Complexity</td>
                            <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontWeight: 600 }}>
                              {result.pipeline_raw.complexity_metrics.cyclomatic_complexity.toFixed(1)}
                            </td>
                          </tr>
                          <tr style={{ borderBottom: '1px solid hsla(var(--border-color), 0.5)' }}>
                            <td style={{ padding: '0.75rem 0.5rem' }}>Maximum Nesting Depth</td>
                            <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontWeight: 600 }}>
                              {result.pipeline_raw.complexity_metrics.max_nesting_depth}
                            </td>
                          </tr>
                          <tr style={{ borderBottom: '1px solid hsla(var(--border-color), 0.5)' }}>
                            <td style={{ padding: '0.75rem 0.5rem' }}>Function Count / Class Count</td>
                            <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontWeight: 600 }}>
                              {result.pipeline_raw.complexity_metrics.function_count} / {result.pipeline_raw.complexity_metrics.class_count}
                            </td>
                          </tr>
                          <tr style={{ borderBottom: '1px solid hsla(var(--border-color), 0.5)' }}>
                            <td style={{ padding: '0.75rem 0.5rem' }}>Loop Count</td>
                            <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontWeight: 600 }}>
                              {result.pipeline_raw.complexity_metrics.loop_count}
                            </td>
                          </tr>
                          <tr style={{ borderBottom: '1px solid hsla(var(--border-color), 0.5)' }}>
                            <td style={{ padding: '0.75rem 0.5rem' }}>Function Density</td>
                            <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', fontWeight: 600 }}>
                              {result.pipeline_raw.complexity_metrics.function_density.toFixed(2)}
                            </td>
                          </tr>
                          <tr>
                            <td style={{ padding: '0.75rem 0.5rem' }}>Active Carbon Intensity Used</td>
                            <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right', color: 'hsl(var(--accent-green))', fontWeight: 600 }}>
                              {result.pipeline_raw.carbon_result.carbon_data.carbon_intensity} gCO₂/kWh ({result.pipeline_raw.carbon_result.carbon_data.zone.zone_key})
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Smell breakdowns */}
                  <div className="section-card animate-stagger" style={{ animationDelay: '450ms' }}>
                    <h4 className="section-title">
                      <AlertTriangle size={18} color="hsl(var(--accent-orange))" /> Smell Categorization
                    </h4>
                    <div style={{ height: '180px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '0.9rem', fontWeight: 600 }}>
                      Detected {result.pipeline_raw.energy_smell_report.findings.length} findings
                    </div>
                    <div>
                      {getFuzzySmellDistributionData().map((d: any, idx: number) => (
                        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: PIE_COLORS[idx % PIE_COLORS.length] }} />
                            {d.name}
                          </span>
                          <span style={{ fontWeight: 'bold' }}>{d.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Findings Table */}
                <div className="section-card animate-stagger" style={{ animationDelay: '500ms' }}>
                  <h4 className="section-title">
                    <Layers size={18} color="hsl(var(--accent-purple))" /> Detected Energy Smells List
                  </h4>
                  <div className="data-table-wrapper" style={{ overflowX: 'auto' }}>
                    <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid hsl(var(--border-color))', textAlign: 'left' }}>
                          <th style={{ padding: '0.75rem 0.5rem', color: 'hsl(var(--text-muted))' }}>Rule ID</th>
                          <th style={{ padding: '0.75rem 0.5rem', color: 'hsl(var(--text-muted))' }}>Category</th>
                          <th style={{ padding: '0.75rem 0.5rem', color: 'hsl(var(--text-muted))' }}>Severity</th>
                          <th style={{ padding: '0.75rem 0.5rem', color: 'hsl(var(--text-muted))' }}>Confidence</th>
                          <th style={{ padding: '0.75rem 0.5rem', color: 'hsl(var(--text-muted))' }}>Line Range</th>
                          <th style={{ padding: '0.75rem 0.5rem', color: 'hsl(var(--text-muted))' }}>Message</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.pipeline_raw.energy_smell_report.findings.length > 0 ? (
                          result.pipeline_raw.energy_smell_report.findings.map((f: any) => (
                            <tr key={f.finding_id} style={{ borderBottom: '1px solid hsla(var(--border-color), 0.3)' }}>
                              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>{f.rule_id}</td>
                              <td style={{ padding: '0.75rem 0.5rem' }}><span className="badge badge-medium" style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', padding: '0.15rem 0.4rem', borderRadius: '4px', fontSize: '0.75rem' }}>{f.category}</span></td>
                              <td style={{ padding: '0.75rem 0.5rem' }}>
                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '0.25rem',
                                  padding: '0.15rem 0.4rem',
                                  borderRadius: '4px',
                                  fontSize: '0.75rem',
                                  fontWeight: 'bold',
                                  background: f.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.15)' : f.severity === 'HIGH' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                                  color: f.severity === 'CRITICAL' ? '#f87171' : f.severity === 'HIGH' ? '#fbbf24' : '#34d399'
                                }}>
                                  {f.severity === 'CRITICAL' && <AlertOctagon size={12} />}
                                  {f.severity === 'HIGH' && <AlertTriangle size={12} />}
                                  {f.severity === 'MEDIUM' && <Info size={12} />}
                                  {f.severity === 'LOW' && <CheckCircle size={12} />}
                                  <span>{f.severity}</span>
                                </span>
                              </td>
                              <td style={{ padding: '0.75rem 0.5rem', fontWeight: 500 }}>{((f.confidence.value || f.confidence) * 100).toFixed(0)}%</td>
                              <td style={{ padding: '0.75rem 0.5rem', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                                {f.line_number ? `L${f.line_number}${f.end_line && f.end_line !== f.line_number ? `-L${f.end_line}` : ''}` : 'N/A'}
                              </td>
                              <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem' }}>{f.message}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={6} style={{ padding: '2rem 0.5rem', textAlign: 'center', color: 'hsl(var(--text-muted))' }}>
                              Zero smells detected! Code is clean.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* RECOMMENDATIONS VIEW */}
        {activeTab === 'recommendations' && (
          <div className="view-wrapper">
            {!result ? (
              <div className="section-card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                <Layers size={40} style={{ color: 'hsl(var(--text-muted))', marginBottom: '1.5rem' }} />
                <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', marginBottom: '0.5rem' }}>
                  No Analysis Loaded
                </h4>
                <p style={{ color: 'hsl(var(--text-secondary))', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                  Please paste code or upload a file on the Home Overview page to begin the predictive green profiling.
                </p>
                <button className="btn btn-primary" onClick={() => setActiveTab('home')}>
                  Go to Home Overview
                </button>
              </div>
            ) : (
              <div>
                <div style={{
                  background: 'hsla(145, 75%, 45%, 0.08)',
                  border: '1px solid hsla(145, 75%, 45%, 0.2)',
                  borderRadius: '12px',
                  padding: '1.25rem 1.5rem',
                  color: 'hsl(var(--accent-green))',
                  fontWeight: 500,
                  fontSize: '0.95rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  marginBottom: '2rem'
                }}>
                  <Info size={18} />
                  <span>{result.recommendations.summary}</span>
                </div>

                <div className="rec-list" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  {result.recommendations.recommendations.map((rec: any) => {
                    const codeExample = rec.code_example || '';
                    const hasAfter = codeExample.includes('# After:');
                    const beforeCode = hasAfter ? codeExample.split('# After:')[0].replace('# Before:', '').trim() : codeExample.trim();
                    const afterCode = hasAfter ? codeExample.split('# After:')[1].trim() : '';

                    return (
                      <div className="rec-card" key={rec.recommendation_id} style={{
                        background: 'hsl(var(--bg-card))',
                        border: '1px solid hsl(var(--border-color))',
                        borderRadius: '16px',
                        padding: '1.75rem',
                        position: 'relative'
                      }}>
                        <div className="rec-meta" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                          <div>
                            <span 
                              className={`badge ${rec.severity === 'CRITICAL' ? 'badge-critical' : rec.severity === 'HIGH' ? 'badge-high' : 'badge-low'}`} 
                              style={{ 
                                marginRight: '0.75rem', 
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                                background: rec.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)', 
                                color: rec.severity === 'CRITICAL' ? '#f87171' : '#fbbf24', 
                                padding: '0.2rem 0.5rem', 
                                borderRadius: '4px', 
                                fontSize: '0.75rem', 
                                fontWeight: 'bold' 
                              }}
                            >
                              {rec.severity === 'CRITICAL' && <AlertOctagon size={12} />}
                              {rec.severity === 'HIGH' && <AlertTriangle size={12} />}
                              {rec.severity === 'MEDIUM' && <Info size={12} />}
                              {rec.severity === 'LOW' && <CheckCircle size={12} />}
                              <span>{rec.severity} Severity</span>
                            </span>
                            <span className="badge badge-medium" style={{ background: 'rgba(255, 255, 255, 0.08)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', color: '#e5e7eb' }}>
                              {rec.category}
                            </span>
                            <h4 className="rec-rule-title" style={{ marginTop: '0.75rem', fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 600 }}>
                              {rec.title}
                            </h4>
                            <p style={{ fontSize: '0.85rem', color: 'hsl(var(--text-muted))', marginTop: '0.2rem' }}>
                              Targeting: {rec.description}
                            </p>
                          </div>

                          <div style={{ textAlign: 'right' }}>
                            <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))', fontWeight: 600, letterSpacing: '0.5px' }}>
                              RISK PRIORITY SCORE
                            </span>
                            <div style={{ 
                              fontSize: '1.8rem', 
                              fontWeight: 800, 
                              color: 'hsl(var(--accent-green))', 
                              fontFamily: 'var(--font-display)',
                              lineHeight: 1.1 
                            }}>
                              {rec.priority_score.toFixed(4)}
                            </div>
                          </div>
                        </div>

                        <p className="rec-explanation" style={{ color: 'hsl(var(--text-secondary))', marginBottom: '1.25rem', fontSize: '0.92rem' }}>
                          {rec.explanation}
                        </p>

                        <div className="rec-fields" style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '1.5rem', marginBottom: '1.5rem', background: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid hsla(var(--border-color), 0.5)' }}>
                          <div>
                            <div className="rec-field-label" style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                              Actionable Optimization
                            </div>
                            <div style={{ color: 'hsl(var(--text-primary))', fontSize: '0.9rem' }}>{rec.optimization_recommendation}</div>
                          </div>
                          <div>
                            <div className="rec-field-label" style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                              Expected Benefit
                            </div>
                            <div style={{ color: 'hsl(var(--accent-green))', fontWeight: 600, fontSize: '0.9rem' }}>{rec.expected_benefit}</div>
                          </div>
                        </div>

                        {codeExample && (
                          <div className="code-container" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
                            <div className="code-panel" style={{ background: '#040711', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '12px', overflow: 'hidden', boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' }}>
                              <div className="code-header before" style={{ background: 'rgba(239, 68, 68, 0.08)', borderBottom: '1px solid rgba(239, 68, 68, 0.15)', padding: '0.5rem 0.75rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#f87171', fontWeight: 600 }}>
                                <span>Before Optimization</span>
                                <span>Inefficient</span>
                              </div>
                              <pre className="code-block" style={{ padding: '1rem', overflowX: 'auto', fontFamily: 'Fira Code, SFMono-Regular, Consolas, Monaco, monospace', fontSize: '0.8rem', lineHeight: '1.5', color: '#c9d1d9', margin: 0 }}>
                                {beforeCode}
                              </pre>
                            </div>

                            <div className="code-panel" style={{ background: '#040711', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '12px', overflow: 'hidden', boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.3)' }}>
                              <div className="code-header after" style={{ background: 'rgba(16, 185, 129, 0.08)', borderBottom: '1px solid rgba(16, 185, 129, 0.15)', padding: '0.5rem 0.75rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>
                                <span>After Optimization</span>
                                <span>Sustainable</span>
                              </div>
                              <pre className="code-block" style={{ padding: '1rem', overflowX: 'auto', fontFamily: 'Fira Code, SFMono-Regular, Consolas, Monaco, monospace', fontSize: '0.8rem', lineHeight: '1.5', color: '#c9d1d9', margin: 0 }}>
                                {afterCode || '# Optimization flattens operational cycle bounds'}
                              </pre>
                            </div>
                          </div>
                        )}

                        {rec.references && rec.references.length > 0 && (
                          <div style={{ 
                            marginTop: '1.25rem', 
                            borderTop: '1px solid hsl(var(--border-color))', 
                            paddingTop: '0.75rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            fontSize: '0.8rem',
                            color: 'hsl(var(--text-muted))'
                          }}>
                            <CheckCircle size={14} color="hsl(var(--accent-green))" />
                            <span>Grounded in research:</span>
                            {rec.references.map((ref: any, idx: number) => (
                              <a 
                                key={idx} 
                                href={ref.url} 
                                target="_blank" 
                                rel="noreferrer" 
                                style={{ color: 'hsl(var(--accent-blue))', textDecoration: 'underline', marginRight: '0.5rem' }}
                              >
                                {ref.title}
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* SETTINGS VIEW */}
        {activeTab === 'settings' && (
          <div className="view-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="section-card">
              <h3 className="section-title" style={{ borderBottom: '1px solid hsl(var(--border-color))', paddingBottom: '0.75rem' }}>
                Searchable Region Selector
              </h3>

              <div style={{ marginTop: '1rem' }}>
                <p style={{ fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', marginBottom: '0.75rem' }}>
                  Choose your marginal grid region to evaluate operational emissions. Currently active: <strong style={{ color: 'hsl(var(--accent-green))' }}>{zone}</strong>
                </p>

                <div className="input-group" style={{ position: 'relative', margin: 0 }}>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <div style={{ position: 'relative', flex: 1 }}>
                      <input 
                        type="text" 
                        className="custom-input" 
                        placeholder="Search zones by code or country name (e.g. India, Denmark, FR)..."
                        value={zoneQuery}
                        onChange={(e) => setZoneQuery(e.target.value)}
                        style={{ paddingLeft: '2.5rem' }}
                      />
                      <Search size={16} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'hsl(var(--text-muted))' }} />
                    </div>
                    {zoneQuery && (
                      <button className="btn btn-secondary" onClick={() => setZoneQuery('')}>
                        Clear Search
                      </button>
                    )}
                  </div>

                  {/* Search Results Display */}
                  {zoneQuery && (
                    <div style={{
                      position: 'absolute',
                      left: 0,
                      right: 0,
                      top: '100%',
                      background: 'hsl(var(--bg-card))',
                      border: '1px solid hsl(var(--border-color))',
                      borderRadius: '8px',
                      marginTop: '0.5rem',
                      maxHeight: '220px',
                      overflowY: 'auto',
                      zIndex: 20,
                      boxShadow: '0 8px 30px rgba(0, 0, 0, 0.4)'
                    }}>
                      {searchingZones ? (
                        <div style={{ padding: '1rem', textAlign: 'center', fontSize: '0.85rem', color: 'hsl(var(--text-secondary))' }}>
                          Searching grid provider database...
                        </div>
                      ) : searchResults.length > 0 ? (
                        searchResults.map((z: any) => {
                          const isCurrent = zone === z.key;
                          return (
                            <div 
                              key={z.key} 
                              onClick={() => {
                                setZone(z.key);
                                setZoneQuery('');
                              }}
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                padding: '0.75rem 1rem',
                                borderBottom: '1px solid hsla(var(--border-color), 0.5)',
                                cursor: 'pointer',
                                fontSize: '0.85rem',
                                background: isCurrent ? 'hsla(var(--accent-green), 0.08)' : 'transparent',
                                transition: 'var(--transition-fast)'
                              }}
                              onMouseEnter={(e) => e.currentTarget.style.background = 'hsl(var(--bg-card-hover))'}
                              onMouseLeave={(e) => e.currentTarget.style.background = isCurrent ? 'hsla(var(--accent-green), 0.08)' : 'transparent'}
                            >
                              <div>
                                <span style={{ fontWeight: 600, color: '#fff' }}>{z.display_name || z.key}</span>
                                <span style={{ color: 'hsl(var(--text-muted))', marginLeft: '0.5rem' }}>({z.country_name || z.key})</span>
                              </div>
                              <div style={{ color: 'hsl(var(--accent-green))', fontWeight: 600 }}>
                                {z.carbon_intensity} gCO₂/kWh
                              </div>
                            </div>
                          );
                        })
                      ) : (
                        <div style={{ padding: '1rem', textAlign: 'center', fontSize: '0.85rem', color: 'hsl(var(--text-muted))' }}>
                          No matching zones found.
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Popular grid zones preview */}
                <div style={{ marginTop: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {zonesList.slice(0, 6).map((z: any) => {
                    const isSelected = zone === z.key;
                    return (
                      <button
                        key={z.key}
                        className={`btn ${isSelected ? 'btn-primary' : 'btn-secondary'}`}
                        style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', borderRadius: '6px' }}
                        onClick={() => setZone(z.key)}
                      >
                        {z.display_name || z.key} ({z.carbon_intensity} g)
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="section-card">
              <h3 className="section-title" style={{ borderBottom: '1px solid hsl(var(--border-color))', paddingBottom: '0.75rem' }}>
                Framework Integrations
              </h3>

              <div className="input-group" style={{ marginTop: '1.5rem', margin: 0 }}>
                <label className="input-label">Electricity Maps API Key</label>
                <input 
                  type="text" 
                  className="custom-input" 
                  value="Configured Securely Server-Side (Read-only via Environment)"
                  disabled
                  style={{ opacity: 0.6, cursor: 'not-allowed' }}
                />
                <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))', marginTop: '0.25rem', display: 'block' }}>
                  The client-side UI is restricted from viewing the raw server API key (defined as `ELECTRICITYMAPS_API_KEY` in the backend environment variables).
                </span>
              </div>
            </div>

            <div className="section-card" style={{
              background: 'linear-gradient(135deg, hsla(265, 80%, 65%, 0.03), transparent)',
              border: '1px dashed hsla(265, 80%, 65%, 0.3)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 className="section-title" style={{ margin: 0 }}>
                    <Code size={18} color="hsl(var(--accent-purple))" /> Carbon-Aware Execution Window Scheduling
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'hsl(var(--text-secondary))', marginTop: '0.5rem' }}>
                    Automatically shifts scheduled execution queues to hours with optimal low-carbon grid predictions.
                  </p>
                </div>
                <span style={{
                  padding: '0.25rem 0.6rem',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 'bold',
                  background: 'rgba(168, 85, 247, 0.15)',
                  color: '#c084fc',
                  border: '1px solid rgba(168, 85, 247, 0.3)'
                }}>
                  Coming soon
                </span>
              </div>
            </div>

            <div className="section-card">
              <h3 className="section-title" style={{ borderBottom: '1px solid hsl(var(--border-color))', paddingBottom: '0.75rem' }}>
                Fuzzy Threshold Configurations
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '1.5rem' }}>
                <div className="input-group">
                  <label className="input-label">Max Nested Loop Depth Allowed</label>
                  <input 
                    type="number" 
                    className="custom-input" 
                    value={maxNestingDepthThreshold}
                    onChange={(e) => setMaxNestingDepthThreshold(parseInt(e.target.value) || 2)}
                  />
                  <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))' }}>
                    Nesting depths exceeding this limit trigger EKB-COMP-001 (Nested Loops) in local reports.
                  </span>
                </div>

                <div className="input-group">
                  <label className="input-label">Concurrency Semaphore Bound</label>
                  <input 
                    type="number" 
                    className="custom-input" 
                    value={concurrencyLimit}
                    onChange={(e) => setConcurrencyLimit(parseInt(e.target.value) || 10)}
                  />
                  <span style={{ fontSize: '0.75rem', color: 'hsl(var(--text-muted))' }}>
                    Concurrency allocations exceeding this bound trigger EKB-CONC-001 in local reports.
                  </span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
              <button className="btn btn-secondary" onClick={() => {
                setConcurrencyLimit(10);
                setMaxNestingDepthThreshold(3);
                setZone('IN');
              }}>Reset Defaults</button>
              <button className="btn btn-primary" onClick={() => {
                alert("Settings updated locally.");
                setActiveTab('home');
              }}>
                Save Settings
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
