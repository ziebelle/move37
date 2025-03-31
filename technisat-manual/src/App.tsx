import { useState, useEffect, useRef } from 'react';
import './App.css';
import manualDataJson from './audiomaster_sl900_manual_en_tabs_constrained.json'; // Import the JSON data

// --- Interfaces for the NEW JSON Schema ---
interface StepContent {
  warning?: string;
  steps: string[];
  note?: string;
}

interface TabInfo {
  id: string; // Unique key for the section, used for assets
  title: string; // Title for the tab
  type: 'list' | 'steps' | 'text'; // Type of content
  content: string[] | StepContent | string; // Content based on type
}

interface ManualData {
  title: string;
  features: string[];
  specialFeatures: string[];
  tabs: TabInfo[]; // Main content organized in tabs
}
// --- End Interfaces ---


function App() {
  // State based on the new structure
  const [manualData, setManualData] = useState<ManualData | null>(null);
  const [activeTabIndex, setActiveTabIndex] = useState(0);
  const [currentSubStepIndex, setCurrentSubStepIndex] = useState(0);
  const [imageError, setImageError] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Load data on mount
  useEffect(() => {
    // Directly cast the imported JSON to our new ManualData interface
    const loadedData = manualDataJson as ManualData;
    setManualData(loadedData);

    // Optionally, set initial tab to the first 'steps' tab if desired
    const firstStepsTabIndex = loadedData.tabs.findIndex(tab => tab.type === 'steps');
    setActiveTabIndex(firstStepsTabIndex >= 0 ? firstStepsTabIndex : 0);

  }, []);

  // Reset image error state when tab or step changes
  useEffect(() => {
    setImageError(false);
  }, [activeTabIndex, currentSubStepIndex]);

  // --- Audio Playback ---
  useEffect(() => {
    if (!manualData?.tabs.length || !audioRef.current) return;

    const currentTab = manualData.tabs[activeTabIndex];
    let audioPath: string | null = null;

    if (currentTab.type === 'steps') {
      // Audio for sub-steps
      audioPath = `/manual_audio/${currentTab.id}_step_${String(currentSubStepIndex).padStart(2, '0')}.wav`;
    } else if (currentTab.type === 'text') {
       // Audio for single text sections
       audioPath = `/manual_audio/${currentTab.id}_main.wav`;
    }
    // Add handling for 'list' type if needed
    // else if (currentTab.type === 'list') {
    //    // Decide if/how to play audio for lists
    // }

    if (audioPath) {
      audioRef.current.src = audioPath;
      audioRef.current.load();
      const playPromise = audioRef.current.play();
      if (playPromise !== undefined) {
        playPromise.catch(error => {
          console.warn(`Audio autoplay prevented for ${audioPath}:`, error);
        });
      }
    } else {
        audioRef.current.removeAttribute('src');
        audioRef.current.load();
    }

    return () => {
        if (audioRef.current && !audioRef.current.paused) {
            audioRef.current.pause();
        }
    };

  }, [activeTabIndex, currentSubStepIndex, manualData]); // Depend on manualData


  // --- Navigation Logic ---
  const activeTab = manualData?.tabs[activeTabIndex];
  const stepsInCurrentTab = activeTab?.type === 'steps' && typeof activeTab.content === 'object' && 'steps' in activeTab.content
    ? activeTab.content.steps.length
    : 0;

  const nextSubStep = () => {
    if (activeTab?.type === 'steps' && currentSubStepIndex < stepsInCurrentTab - 1) {
      setCurrentSubStepIndex((prev) => prev + 1);
    }
  };

  const prevSubStep = () => {
    if (activeTab?.type === 'steps' && currentSubStepIndex > 0) {
      setCurrentSubStepIndex((prev) => prev - 1);
    }
  };

  const selectTab = (index: number) => {
    setActiveTabIndex(index);
    setCurrentSubStepIndex(0); // Reset sub-step when changing tab
  };

  // --- Keyboard Navigation ---
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (activeTab?.type === 'steps') { // Navigate sub-steps only if current tab is 'steps' type
        if (event.key === 'ArrowRight') {
          nextSubStep();
        } else if (event.key === 'ArrowLeft') {
          prevSubStep();
        }
      }
      // You could add ArrowUp/Down for tab switching if desired
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [activeTab, currentSubStepIndex, stepsInCurrentTab]); // Dependencies updated


  // --- Rendering Logic ---
  const handleImageError = () => {
    console.warn(`Image not found or failed to load.`);
    setImageError(true);
  };

  const renderActiveTabContent = () => {
    if (!activeTab) return <div>Select a tab</div>;

    const { id: tabId, type, content } = activeTab;

    switch (type) {
      case 'steps':
        if (typeof content !== 'object' || !('steps' in content)) return null; // Type guard
        const stepContent = content as StepContent; // Cast for easier access
        const stepText = stepContent.steps[currentSubStepIndex];
        const imagePath = `/manual_images/${tabId}_step_${String(currentSubStepIndex + 1).padStart(2, '0')}.png`;
        const isEvenStep = currentSubStepIndex % 2 === 0;
        const layoutClass = isEvenStep ? 'layout-image-right' : 'layout-image-left';
        const animationKey = `${activeTabIndex}-${currentSubStepIndex}`;

        return (
          <div key={animationKey} className="step-content single-step animate-fade-in">
            {stepContent.warning && currentSubStepIndex === 0 && <p className="warning"><strong>Warning:</strong> {stepContent.warning}</p>}
            <div className={`split-layout ${layoutClass}`}>
              <div className="text-half">
                <p><span>{currentSubStepIndex + 1}.</span> {stepText}</p>
              </div>
              <div className="image-half">
                {!imageError ? (
                    <img
                      key={imagePath}
                      src={imagePath}
                      alt={`Illustration for ${tabId} step ${currentSubStepIndex + 1}`}
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
        if (!Array.isArray(content)) return null; // Type guard
        return (
          <div className="step-content list-content">
            <ul>
              {(content as string[]).map((item, index) => <li key={index}>{item}</li>)}
            </ul>
          </div>
        );

      case 'text':
        if (typeof content !== 'string') return null; // Type guard
        return (
          <div className="step-content single-text">
              <p>{content}</p>
          </div>
        );

      default:
        return <div>Unsupported tab type.</div>;
    }
  };

  if (!manualData) {
    return <div>Loading manual...</div>;
  }

  return (
    <div className="App">
      <header>
        <h1>{manualData.title}</h1>
        {/* Tab Navigation using manualData.tabs */}
        <nav className="tabs">
          {manualData.tabs.map((tab, index) => (
            <button
              key={tab.id}
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
        {/* Navigation for sub-steps (only show if active tab is 'steps' type) */}
        {activeTab?.type === 'steps' && (
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
      {/* Add the audio element (hidden) */}
      <audio ref={audioRef} style={{ display: 'none' }} />
    </div>
  );
}

export default App;
