import { useState, useEffect, useRef } from 'react';
import './App.css';
// Removed static JSON import: import manualDataJson from './audiomaster_sl900_manual_en_tabs_constrained.json';

// --- Interfaces reflecting the API/DB structure ---
interface StepData {
    id: string; // e.g., "hardwareInstallation_step_00"
    text: string;
    // Warning/Note are associated with the overall StepContentData now
}

interface StepContentData {
  warning?: string;
  steps: StepData[];
  note?: string;
}

interface ListItemData {
  id: string; // e.g., "systemRequirements_item_00"
  text: string;
}

interface TabInfo {
  tab_id: number; // From DB
  tab_key: string; // e.g., "hardwareInstallation" (used for assets)
  title: string; // Tab Title
  tab_order: number;
  content_type: 'list' | 'steps' | 'text';
  content: ListItemData[] | StepContentData | string; // Structure depends on content_type
}

interface ManualData {
  manual_id: number;
  title: string;
  source_path: string;
  features?: string[]; // Optional
  special_features?: string[]; // Optional
  tabs: TabInfo[];
}
// --- End Interfaces ---

// --- API Configuration ---
const API_BASE_URL = 'http://localhost:5001'; // Adjust if your backend runs elsewhere
// --- End API Configuration ---


function App() {
  // State for fetched data, loading, and errors
  const [manualData, setManualData] = useState<ManualData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true); // Start loading initially
  const [error, setError] = useState<string | null>(null);
  // State for UI interaction
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [currentSubStepIndex, setCurrentSubStepIndex] = useState(0);
  const [imageError, setImageError] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // --- Data Fetching ---
  useEffect(() => {
    // Fetch data for a specific manual (e.g., ID 1 for now)
    // In a real app, you might fetch a list first or get ID from URL/props
    const manualIdToLoad = 1; // Example: Load the first manual inserted
    fetchManualData(manualIdToLoad);
  }, []); // Run only once on mount

  const fetchManualData = async (manualId: number) => {
    setIsLoading(true);
    setError(null);
    setManualData(null); // Clear old data
    setActiveTabIndex(0); // Reset tab
    setCurrentSubStepIndex(0); // Reset step

    try {
      const response = await fetch(`${API_BASE_URL}/api/manuals/${manualId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data: ManualData = await response.json();
      setManualData(data);

      // Set initial tab (e.g., first 'steps' tab or just the first tab)
      const firstStepsTabIndex = data.tabs.findIndex(tab => tab.content_type === 'steps');
      setActiveTabIndex(firstStepsTabIndex >= 0 ? firstStepsTabIndex : 0);

    } catch (e) {
      console.error("Failed to fetch manual data:", e);
      setError(e instanceof Error ? e.message : "An unknown error occurred");
    } finally {
      setIsLoading(false);
    }
  };
  // --- End Data Fetching ---


  // Reset image error state when tab or step changes
  useEffect(() => {
    setImageError(false);
  }, [activeTabIndex, currentSubStepIndex]);

  // --- Audio Playback ---
  useEffect(() => {
    // Guard clauses
    if (isLoading || error || !manualData?.tabs.length || !audioRef.current) {
        // Stop playback if loading, error, or no data
        if (audioRef.current && !audioRef.current.paused) {
            audioRef.current.pause();
            audioRef.current.removeAttribute('src');
            audioRef.current.load();
        }
        return;
    }

    const currentTab = manualData.tabs[activeTabIndex];
    let audioPath: string | null = null;
    let audioId: string | null = null; // To construct filename

    if (currentTab.content_type === 'steps') {
        const stepsContent = currentTab.content as StepContentData;
        if (stepsContent.steps && currentSubStepIndex < stepsContent.steps.length) {
            // Use the step's specific ID for the filename
            audioId = stepsContent.steps[currentSubStepIndex].id;
        }
    } else if (currentTab.content_type === 'text') {
       audioId = `${currentTab.tab_key}_main`; // Use tab_key for main text audio
    } else if (currentTab.content_type === 'list') {
        // Play audio for the first list item when tab is selected
        const listContent = currentTab.content as ListItemData[];
        if (listContent && listContent.length > 0) {
            audioId = listContent[0].id; // Use first item's ID
        }
    }

    if (audioId) {
        audioPath = `/manual_audio/${audioId}.wav`;
    }

    // Play logic remains similar
    if (audioPath && audioRef.current.src !== `${window.location.origin}${audioPath}`) { // Avoid reloading same src
      console.log("Attempting to play audio:", audioPath);
      audioRef.current.src = audioPath;
      audioRef.current.load();
      const playPromise = audioRef.current.play();
      if (playPromise !== undefined) {
        playPromise.catch(err => {
          console.warn(`Audio autoplay prevented for ${audioPath}:`, err);
        });
      }
    } else if (!audioPath) {
        if (audioRef.current.src) { // Only clear if there was a source
             audioRef.current.pause();
             audioRef.current.removeAttribute('src');
             audioRef.current.load();
        }
    }

    // Cleanup handled by dependency changes triggering the effect again

  }, [activeTabIndex, currentSubStepIndex, manualData, isLoading, error]); // Added isLoading/error


  // --- Navigation Logic ---
  const activeTab = manualData?.tabs[activeTabIndex];
  const stepsInCurrentTab = activeTab?.content_type === 'steps' && typeof activeTab.content === 'object' && 'steps' in activeTab.content
    ? (activeTab.content as StepContentData).steps.length
    : 0;

  const nextSubStep = () => {
    if (activeTab?.content_type === 'steps' && currentSubStepIndex < stepsInCurrentTab - 1) {
      setCurrentSubStepIndex((prev) => prev + 1);
    }
  };

  const prevSubStep = () => {
    if (activeTab?.content_type === 'steps' && currentSubStepIndex > 0) {
      setCurrentSubStepIndex((prev) => prev - 1);
    }
  };

  const selectTab = (index: number) => {
    setActiveTabIndex(index);
    setCurrentSubStepIndex(0);
  };

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
  const handleImageError = () => {
    console.warn(`Image not found or failed to load.`);
    setImageError(true);
  };

  const renderActiveTabContent = () => {
    if (!activeTab) return <div>Select a tab</div>; // Should not happen if manualData exists

    const { tab_key: tabKey, content_type, content } = activeTab; // Use tab_key from DB

    switch (content_type) {
      case 'steps':
        if (typeof content !== 'object' || !('steps' in content)) return null;
        const stepContent = content as StepContentData;
        if (!stepContent.steps || currentSubStepIndex >= stepContent.steps.length) return <div>Invalid step index.</div>;

        const currentStep = stepContent.steps[currentSubStepIndex];
        // Use step ID for assets
        const assetBaseName = currentStep.id;
        const imagePath = `/manual_images/${assetBaseName}.png`;

        const isEvenStep = currentSubStepIndex % 2 === 0;
        const layoutClass = isEvenStep ? 'layout-image-right' : 'layout-image-left';
        const animationKey = `${activeTabIndex}-${currentSubStepIndex}`;

        return (
          <div key={animationKey} className="step-content single-step animate-fade-in">
            {stepContent.warning && currentSubStepIndex === 0 && <p className="warning"><strong>Warning:</strong> {stepContent.warning}</p>}
            <div className={`split-layout ${layoutClass}`}>
              <div className="text-half">
                <p><span>{currentSubStepIndex + 1}.</span> {currentStep.text}</p>
              </div>
              <div className="image-half">
                {!imageError ? (
                    <img
                      key={imagePath}
                      src={imagePath}
                      alt={`Illustration for ${tabKey} step ${currentSubStepIndex + 1}`}
                      className="step-image"
                      onError={handleImageError}
                    />
                ) : (
                   <div className="image-placeholder">Image not available</div>
                )}
              </div>
            </div>
            {stepContent.note && currentSubStepIndex === stepContent.steps.length - 1 && <p className="note"><em>Note:</em> {stepContent.note}</p>}
          </div>
        );

      case 'list':
        if (!Array.isArray(content) || !content.every(item => typeof item === 'object' && 'id' in item && 'text' in item)) return null;
        return (
          <div className="step-content list-content">
            <ul>
              {(content as ListItemData[]).map((item) => <li key={item.id}>{item.text}</li>)}
            </ul>
          </div>
        );

      case 'text':
        if (typeof content !== 'string') return null;
        return (
          <div className="step-content single-text">
              <p>{content}</p>
          </div>
        );

      default:
        console.warn("Unsupported tab type:", content_type);
        return <div>Unsupported tab type.</div>;
    }
  };

  // --- Main Return ---
  if (isLoading) return <div className="loading-message">Loading Manual...</div>;
  if (error) return <div className="error-message">Error loading manual: {error}</div>;
  if (!manualData) return <div className="error-message">No manual data loaded.</div>; // Should not happen if loading/error handled

  return (
    <div className="App">
      <header>
        <h1>{manualData.title}</h1>
        <nav className="tabs">
          {manualData.tabs.map((tab, index) => (
            <button
              key={tab.tab_key} // Use stable tab_key from DB
              className={`tab ${index === activeTabIndex ? 'active' : ''}`}
              onClick={() => selectTab(index)}
            >
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
            <button onClick={prevSubStep} disabled={currentSubStepIndex === 0}>
              Back
            </button>
            <div className="progress-indicator">
              Step {currentSubStepIndex + 1} of {stepsInCurrentTab}
            </div>
            <button onClick={nextSubStep} disabled={currentSubStepIndex === stepsInCurrentTab - 1}>
              Next
            </button>
          </div>
        )}
      </main>
      <audio ref={audioRef} style={{ display: 'none' }} />
    </div>
  );
}

export default App;
