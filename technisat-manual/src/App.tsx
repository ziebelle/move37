import { useState, useEffect, useRef } from 'react'; // Added useRef
import './App.css';
import manualData from './bda_en.json'; // Import the English JSON data

// Define interfaces for the structure of the manual data
interface ManualData {
  title: string;
  features: string[];
  specialFeatures: string[];
  systemRequirements: string[];
  mediaFocusCardInstallation: StepSection;
  driverInstallation: StepSection;
  applicationSoftwareInstallation: StepSection;
  launchingApplicationPrograms: string;
}

interface StepSection {
  warning?: string;
  steps: string[];
  note?: string;
}

// Define structure for our sections/tabs
interface SectionInfo {
  id: string; // Unique key for the section
  title: string; // Title for the tab
  content: string[] | StepSection; // Content type
  hasSubSteps: boolean; // Does this section have navigable sub-steps?
  imageKey?: string; // Key used for image filenames (if hasSubSteps)
  isSingleText?: boolean; // Flag for single text sections like 'launch'
}


function App() {
  const [data, setData] = useState<ManualData | null>(null);
  const [sections, setSections] = useState<SectionInfo[]>([]);
  const [activeSectionIndex, setActiveSectionIndex] = useState(0);
  const [currentSubStepIndex, setCurrentSubStepIndex] = useState(0);
  const [imageError, setImageError] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null); // Ref for the audio element

  // Load and structure data on mount
  useEffect(() => {
    const loadedData = manualData as ManualData;
    setData(loadedData);

    // Define the sections based on the loaded data
    const structuredSections: SectionInfo[] = [
      { id: 'sysReq', title: 'System Requirements', content: loadedData.systemRequirements, hasSubSteps: false },
      { id: 'hwInstall', title: 'Hardware Install', content: loadedData.mediaFocusCardInstallation, hasSubSteps: true, imageKey: 'install_card' },
      { id: 'driverInstall', title: 'Driver Install', content: loadedData.driverInstallation, hasSubSteps: true, imageKey: 'install_driver' },
      { id: 'swInstall', title: 'Software Install', content: loadedData.applicationSoftwareInstallation, hasSubSteps: true, imageKey: 'install_software' },
      { id: 'launch', title: 'Launch App', content: { steps: [loadedData.launchingApplicationPrograms] }, hasSubSteps: false, isSingleText: true }, // Added isSingleText flag
    ];
    setSections(structuredSections);
    // Start at the first section that has steps (usually Hardware Install)
    const firstStepSectionIndex = structuredSections.findIndex(s => s.hasSubSteps);
    setActiveSectionIndex(firstStepSectionIndex >= 0 ? firstStepSectionIndex : 0);

  }, []);

  // Reset image error state when section or step changes
  useEffect(() => {
    setImageError(false);
  }, [activeSectionIndex, currentSubStepIndex]);

  // --- Audio Playback ---
  useEffect(() => {
    if (!sections.length || !audioRef.current) return; // Ensure sections are loaded and ref exists

    const currentSection = sections[activeSectionIndex];
    let audioPath: string | null = null;

    if (currentSection.hasSubSteps) {
      // Audio for sub-steps
      audioPath = `/manual_audio/${currentSection.id}_step_${String(currentSubStepIndex).padStart(2, '0')}.wav`;
    } else if (currentSection.isSingleText) {
       // Audio for single text sections
       audioPath = `/manual_audio/${currentSection.id}_main.wav`;
    }
    // Note: No audio playback for list-based sections like System Requirements currently

    if (audioPath) {
      audioRef.current.src = audioPath;
      audioRef.current.load(); // Load the new source
      const playPromise = audioRef.current.play();

      if (playPromise !== undefined) {
        playPromise.then(_ => {
          // Autoplay started!
        }).catch(error => {
          // Autoplay was prevented.
          console.warn(`Audio autoplay prevented for ${audioPath}:`, error);
          // You could potentially show a play button here if needed
        });
      }
    } else {
        // No audio for this step/section, ensure src is cleared
        audioRef.current.removeAttribute('src');
        audioRef.current.load();
    }

    // Cleanup: Pause audio if component unmounts or dependencies change before playback finishes
    return () => {
        if (audioRef.current && !audioRef.current.paused) {
            audioRef.current.pause();
        }
    };

  }, [activeSectionIndex, currentSubStepIndex, sections]); // Depend on sections as well


  // --- Navigation Logic ---
  const activeSection = sections[activeSectionIndex];
  const stepsInCurrentSection = activeSection?.hasSubSteps && 'steps' in activeSection.content
    ? activeSection.content.steps.length
    : 0;

  const nextSubStep = () => {
    if (activeSection?.hasSubSteps && currentSubStepIndex < stepsInCurrentSection - 1) {
      setCurrentSubStepIndex((prev) => prev + 1);
    }
  };

  const prevSubStep = () => {
    if (activeSection?.hasSubSteps && currentSubStepIndex > 0) {
      setCurrentSubStepIndex((prev) => prev - 1);
    }
  };

  const selectSection = (index: number) => {
    setActiveSectionIndex(index);
    setCurrentSubStepIndex(0); // Reset sub-step when changing section
  };

  // --- Keyboard Navigation ---
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (activeSection?.hasSubSteps) {
        if (event.key === 'ArrowRight') {
          nextSubStep();
        } else if (event.key === 'ArrowLeft') {
          prevSubStep();
        }
      }
      // Add tab navigation? (Optional)
      // else if (event.key === 'ArrowRight') {
      //   selectSection(Math.min(activeSectionIndex + 1, sections.length - 1));
      // } else if (event.key === 'ArrowLeft') {
      //   selectSection(Math.max(activeSectionIndex - 1, 0));
      // }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [activeSection, currentSubStepIndex, stepsInCurrentSection, activeSectionIndex, sections.length]); // Added dependencies


  // --- Rendering Logic ---
  const handleImageError = () => {
    console.warn(`Image not found or failed to load.`);
    setImageError(true);
  };

  const renderActiveSectionContent = () => {
    if (!activeSection) return <div>Select a section</div>;
    const { content, hasSubSteps, imageKey } = activeSection;

    if (hasSubSteps && 'steps' in content) {
      const stepText = content.steps[currentSubStepIndex];
      const imagePath = imageKey ? `/manual_images/${imageKey}_step_${String(currentSubStepIndex + 1).padStart(2, '0')}.png` : null;
      const isEvenStep = currentSubStepIndex % 2 === 0;
      const layoutClass = isEvenStep ? 'layout-image-right' : 'layout-image-left';
      const animationKey = `${activeSectionIndex}-${currentSubStepIndex}`;

      return (
        <div key={animationKey} className="step-content single-step animate-fade-in">
          {content.warning && currentSubStepIndex === 0 && <p className="warning"><strong>Warning:</strong> {content.warning}</p>}
          <div className={`split-layout ${layoutClass}`}>
            <div className="text-half">
              <p><span>{currentSubStepIndex + 1}.</span> {stepText}</p>
            </div>
            <div className="image-half">
              {imagePath && !imageError ? (
                  <img
                    key={imagePath}
                    src={imagePath}
                    alt={`Illustration for ${imageKey} step ${currentSubStepIndex + 1}`}
                    className="step-image"
                    onError={handleImageError}
                  />
              ) : (
                 <div className="image-placeholder">
                    {imagePath ? 'Image not available' : 'No image for this step'}
                 </div>
              )}
            </div>
          </div>
          {content.note && currentSubStepIndex === content.steps.length - 1 && <p className="note"><em>Note:</em> {content.note}</p>}
        </div>
      );
    } else if (Array.isArray(content)) {
      return (
        <div className="step-content list-content">
          <ul>
            {content.map((item, index) => <li key={index}>{item}</li>)}
          </ul>
        </div>
      );
    } else if ('steps' in content) { // Handles single text sections now
         return (
            <div className="step-content single-text">
                <p>{content.steps[0]}</p>
            </div>
         );
    }
    return <div>Content type not recognized.</div>;
  };

  if (!data || sections.length === 0) {
    return <div>Loading manual...</div>;
  }

  return (
    <div className="App">
      <header>
        <h1>{data.title}</h1>
        <nav className="tabs">
          {sections.map((section, index) => (
            <button
              key={section.id}
              className={`tab ${index === activeSectionIndex ? 'active' : ''}`}
              onClick={() => selectSection(index)}
            >
              {section.title}
            </button>
          ))}
        </nav>
      </header>

      <main>
        <div className="steps-container">
          {renderActiveSectionContent()}
        </div>
        {activeSection?.hasSubSteps && (
          <div className="navigation-buttons">
            <button onClick={prevSubStep} disabled={currentSubStepIndex === 0}>
              Back
            </button>
            <div className="progress-indicator">
              Step {currentSubStepIndex + 1} of {stepsInCurrentSection}
            </div>
            <button onClick={nextSubStep} disabled={currentSubStepIndex === stepsInCurrentSection - 1}>
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
