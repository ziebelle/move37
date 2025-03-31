import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom'; // Added Link for back button
import './App.css'; // Reuse existing App styles for the viewer

// --- Interfaces (Copied from previous App.tsx, adjust if needed) ---
interface StepData {
    id: string;
    text: string;
}
interface StepContentData {
  warning?: string;
  steps: StepData[];
  note?: string;
}
interface ListItemData {
  id: string;
  text: string;
}
interface TabInfo {
  tab_id: number;
  tab_key: string;
  title: string;
  tab_order: number;
  content_type: 'list' | 'steps' | 'text';
  content: ListItemData[] | StepContentData | string;
}
interface ManualData {
  manual_id: number;
  title: string;
  source_path: string;
  features?: string[];
  special_features?: string[];
  tabs: TabInfo[];
}
// --- End Interfaces ---

// --- API Configuration ---
const API_BASE_URL = 'http://localhost:5001'; // Adjust if needed
// --- End API Configuration ---


function ManualViewerPage() {
  const { manualId } = useParams<{ manualId: string }>(); // Get manualId from URL
  const [manualData, setManualData] = useState<ManualData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [currentSubStepIndex, setCurrentSubStepIndex] = useState(0);
  const [imageError, setImageError] = useState(false);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true); // <-- New state for audio toggle
  const audioRef = useRef<HTMLAudioElement>(null);

  // --- Data Fetching ---
  useEffect(() => {
    if (!manualId) {
        setError("Manual ID not found in URL.");
        setIsLoading(false);
        return;
    }
    const fetchManualData = async (id: number) => {
        setIsLoading(true); setError(null); setManualData(null);
        setActiveTabIndex(0); setCurrentSubStepIndex(0); setImageError(false);
        try {
            const response = await fetch(`${API_BASE_URL}/api/manuals/${id}`);
            if (!response.ok) {
                 if (response.status === 404) throw new Error(`Manual with ID ${id} not found.`);
                 else throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data: ManualData = await response.json();
            setManualData(data);
            const firstStepsTabIndex = data.tabs.findIndex(tab => tab.content_type === 'steps');
            setActiveTabIndex(firstStepsTabIndex >= 0 ? firstStepsTabIndex : 0);
        } catch (e) {
            console.error("Failed to fetch manual data:", e);
            setError(e instanceof Error ? e.message : "An unknown error occurred");
        } finally { setIsLoading(false); }
    };
    fetchManualData(parseInt(manualId, 10));
  }, [manualId]);

  // Reset image error state when tab or step changes
  useEffect(() => { setImageError(false); }, [activeTabIndex, currentSubStepIndex]);

  // --- Audio Playback ---
  useEffect(() => {
    const audioEl = audioRef.current;
    if (!audioEl) return;
    if (!isAudioEnabled || isLoading || error || !manualData?.tabs.length) {
        if (!audioEl.paused) audioEl.pause();
        if (audioEl.src) { audioEl.removeAttribute('src'); audioEl.load(); }
        return;
    }
    const currentTab = manualData.tabs[activeTabIndex];
    let audioPath: string | null = null; let audioId: string | null = null;
    if (currentTab.content_type === 'steps') {
        const stepsContent = currentTab.content as StepContentData;
        if (stepsContent.steps && currentSubStepIndex < stepsContent.steps.length) audioId = stepsContent.steps[currentSubStepIndex].id;
    } else if (currentTab.content_type === 'text') { audioId = `${currentTab.tab_key}_main`;
    } else if (currentTab.content_type === 'list') {
        const listContent = currentTab.content as ListItemData[];
        if (listContent && listContent.length > 0 && currentSubStepIndex === 0) audioId = listContent[0].id;
    }
    if (audioId) audioPath = `/manual_audio/${audioId}.wav`;
    const currentSrc = audioEl.currentSrc || audioEl.src;
    const newSrc = audioPath ? `${window.location.origin}${audioPath}` : null;
    if (audioPath && currentSrc !== newSrc) {
        console.log("Attempting to play audio:", audioPath);
        audioEl.src = audioPath; audioEl.load();
        const playPromise = audioEl.play();
        if (playPromise !== undefined) playPromise.catch(err => console.warn(`Audio autoplay prevented for ${audioPath}:`, err));
    } else if (!audioPath && currentSrc) {
        audioEl.pause(); audioEl.removeAttribute('src'); audioEl.load();
    }
  }, [activeTabIndex, currentSubStepIndex, manualData, isLoading, error, isAudioEnabled]);


  // --- Navigation Logic ---
  const activeTab = manualData?.tabs[activeTabIndex];
  const stepsInCurrentTab = activeTab?.content_type === 'steps' && typeof activeTab.content === 'object' && 'steps' in activeTab.content ? (activeTab.content as StepContentData).steps.length : 0;
  const nextSubStep = () => { if (activeTab?.content_type === 'steps' && currentSubStepIndex < stepsInCurrentTab - 1) setCurrentSubStepIndex(prev => prev + 1); };
  const prevSubStep = () => { if (activeTab?.content_type === 'steps' && currentSubStepIndex > 0) setCurrentSubStepIndex(prev => prev - 1); };
  const selectTab = (index: number) => { setActiveTabIndex(index); setCurrentSubStepIndex(0); };

  // --- Keyboard Navigation ---
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (activeTab?.content_type === 'steps') {
        if (event.key === 'ArrowRight') nextSubStep();
        else if (event.key === 'ArrowLeft') prevSubStep();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, currentSubStepIndex, stepsInCurrentTab]);


  // --- Rendering Logic ---
  const handleImageError = () => { console.warn(`Image not found or failed to load.`); setImageError(true); };

  const renderActiveTabContent = () => {
    if (!activeTab) return null;
    const { tab_key: tabKey, content_type, content } = activeTab;
    switch (content_type) {
      case 'steps':
        if (typeof content !== 'object' || !('steps' in content)) return null;
        const stepContent = content as StepContentData;
        if (!stepContent.steps || currentSubStepIndex >= stepContent.steps.length) return <div>Invalid step index.</div>;
        const currentStep = stepContent.steps[currentSubStepIndex];
        const assetBaseName = currentStep.id;
        const imagePath = `/manual_images/${assetBaseName}.png`;
        const isEvenStep = currentSubStepIndex % 2 === 0;
        const layoutClass = isEvenStep ? 'layout-image-right' : 'layout-image-left';
        const animationKey = `${activeTabIndex}-${currentSubStepIndex}`;
        return (
          <div key={animationKey} className="step-content single-step animate-fade-in">
            {stepContent.warning && currentSubStepIndex === 0 && <p className="warning"><strong>Warning:</strong> {stepContent.warning}</p>}
            <div className={`split-layout ${layoutClass}`}>
              <div className="text-half"><p><span>{currentSubStepIndex + 1}.</span> {currentStep.text}</p></div>
              <div className="image-half">
                {!imageError ? (<img key={imagePath} src={imagePath} alt={`Illustration for ${tabKey} step ${currentSubStepIndex + 1}`} className="step-image" onError={handleImageError}/>)
                 : (<div className="image-placeholder">Image not available</div>)}
              </div>
            </div>
            {stepContent.note && currentSubStepIndex === stepContent.steps.length - 1 && <p className="note"><em>Note:</em> {stepContent.note}</p>}
          </div>
        );
      case 'list':
        if (!Array.isArray(content) || !content.every(item => typeof item === 'object' && 'id' in item && 'text' in item)) return null;
        return (<div className="step-content list-content"><ul>{(content as ListItemData[]).map((item) => <li key={item.id}>{item.text}</li>)}</ul></div>);
      case 'text':
        if (typeof content !== 'string') return null;
        return (<div className="step-content single-text"><p>{content}</p></div>);
      default: console.warn("Unsupported tab type:", content_type); return <div>Unsupported tab type.</div>;
    }
  };

  // --- Main Return ---
  if (isLoading) return <div className="loading-message">Loading Manual {manualId}...</div>;
  if (error) return <div className="error-message">Error loading manual {manualId}: {error} <Link to="/">Back to list</Link></div>;
  if (!manualData) return <div className="error-message">No data found for manual {manualId}. <Link to="/">Back to list</Link></div>;

  return (
    // Add position: relative here if not already on body/#root
    <div className="App manual-viewer">
       {/* Audio Toggle Button - Positioned Absolutely via CSS */}
       <button
            onClick={() => setIsAudioEnabled(!isAudioEnabled)}
            className={`audio-toggle ${isAudioEnabled ? 'enabled' : 'disabled'}`}
            title={isAudioEnabled ? 'Disable Audio' : 'Enable Audio'}
        >
            {isAudioEnabled ? '🔊' : '🔇'}
        </button>

      <header>
        {/* Keep header content centered */}
        <div className="header-content">
            <Link to="/" className="back-link">← Manuals</Link>
            <h1>{manualData.title}</h1>
            {/* Placeholder to balance the back link, keeps title centered */}
            <span className="header-spacer"></span>
        </div>
        <nav className="tabs">
          {manualData.tabs.map((tab, index) => (
            <button key={tab.tab_key} className={`tab ${index === activeTabIndex ? 'active' : ''}`} onClick={() => selectTab(index)}>
              {tab.title}
            </button>
          ))}
        </nav>
      </header>

      <main>
        <div className="steps-container">
          {renderActiveTabContent()}
        </div>
        {activeTab?.content_type === 'steps' && (
          <div className="navigation-buttons">
            <button onClick={prevSubStep} disabled={currentSubStepIndex === 0}>Back</button>
            <div className="progress-indicator">Step {currentSubStepIndex + 1} of {stepsInCurrentTab}</div>
            <button onClick={nextSubStep} disabled={currentSubStepIndex === stepsInCurrentTab - 1}>Next</button>
          </div>
        )}
      </main>
      <audio ref={audioRef} style={{ display: 'none' }} />
    </div>
  );
}

export default ManualViewerPage;