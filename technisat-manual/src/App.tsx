import { useState, useEffect } from 'react';
import './App.css';
import manualData from './bda_en.json'; // Import the English JSON data

// Define interfaces for the structure of the manual data
interface ManualData {
  title: string;
  features: string[]; // Keep for potential future use, but not displayed in tabs
  specialFeatures: string[]; // Keep for potential future use
  systemRequirements: string[]; // Will be a section
  mediaFocusCardInstallation: StepSection;
  driverInstallation: StepSection;
  applicationSoftwareInstallation: StepSection;
  launchingApplicationPrograms: string; // Will be a section
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
}


function App() {
  const [data, setData] = useState<ManualData | null>(null);
  const [sections, setSections] = useState<SectionInfo[]>([]);
  const [activeSectionIndex, setActiveSectionIndex] = useState(0);
  const [currentSubStepIndex, setCurrentSubStepIndex] = useState(0);

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
      { id: 'launch', title: 'Launch App', content: { steps: [loadedData.launchingApplicationPrograms] }, hasSubSteps: false }, // Treat as StepSection for consistency, but no sub-steps/images
    ];
    setSections(structuredSections);
    // Start at the first section that has steps (usually Hardware Install)
    const firstStepSectionIndex = structuredSections.findIndex(s => s.hasSubSteps);
    setActiveSectionIndex(firstStepSectionIndex >= 0 ? firstStepSectionIndex : 0);

  }, []);

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

  // --- Rendering Logic ---

  // Function to handle image loading errors
  const handleImageError = (event: React.SyntheticEvent<HTMLImageElement, Event>) => {
    event.currentTarget.style.display = 'none'; // Hide broken image
    console.warn(`Image not found or failed to load: ${event.currentTarget.src}`);
  };

  const renderActiveSectionContent = () => {
    if (!activeSection) return <div>Select a section</div>;

    const { content, hasSubSteps, imageKey } = activeSection;

    if (hasSubSteps && 'steps' in content) {
      // Render current sub-step with image
      const stepText = content.steps[currentSubStepIndex];
      const imagePath = imageKey
        ? `/manual_images/${imageKey}_step_${String(currentSubStepIndex + 1).padStart(2, '0')}.png`
        : null;

      return (
        <div className="step-content single-step">
          {/* Display warning/note only if relevant to the current step? Or always for the section? Let's show always for now */}
          {content.warning && currentSubStepIndex === 0 && <p className="warning"><strong>Warning:</strong> {content.warning}</p>}
          <div className="step-text-image">
            <p>{currentSubStepIndex + 1}. {stepText}</p>
            {imagePath && (
              <img
                key={imagePath} // Add key to force re-render on change
                src={imagePath}
                alt={`Illustration for ${imageKey} step ${currentSubStepIndex + 1}`}
                className="step-image"
                onError={handleImageError}
              />
            )}
          </div>
          {content.note && currentSubStepIndex === content.steps.length - 1 && <p className="note"><em>Note:</em> {content.note}</p>}
        </div>
      );
    } else if (Array.isArray(content)) {
      // Render list content (e.g., System Requirements)
      return (
        <div className="step-content list-content">
          <ul>
            {content.map((item, index) => <li key={index}>{item}</li>)}
          </ul>
        </div>
      );
    } else if ('steps' in content) {
        // Render single text content (e.g., Launch App)
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
        {/* Tab Navigation */}
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
        {/* Render only the active section's content */}
        <div className="steps-container">
          {renderActiveSectionContent()}
        </div>

        {/* Navigation for sub-steps (only show if section has sub-steps) */}
        {activeSection?.hasSubSteps && (
          <div className="navigation-buttons"> {/* Container for buttons and progress */}
            <button onClick={prevSubStep} disabled={currentSubStepIndex === 0}>
              Back
            </button>
            {/* Moved progress indicator inside */}
            <div className="progress-indicator">
              Step {currentSubStepIndex + 1} of {stepsInCurrentSection}
              {/* Optionally add section title back if needed: in {activeSection.title} */}
            </div>
            <button onClick={nextSubStep} disabled={currentSubStepIndex === stepsInCurrentSection - 1}>
              Next
            </button>
          </div>
        )}
      </main>

      <footer>
        <p>Interactive Manual</p>
      </footer>
    </div>
  );
}

export default App;
