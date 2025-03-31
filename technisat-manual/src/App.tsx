import { useState, useEffect } from 'react';
import './App.css';
import manualData from './bda_en.json'; // Import the English JSON data

// Define an interface for the structure of the manual data
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

// Map section index to the key used in filenames
const sectionKeys: { [key: number]: string } = {
  0: "install_card",
  1: "install_driver",
  2: "install_software",
  // No key for index 3 (final step)
};

function App() {
  const [currentSectionIndex, setCurrentSectionIndex] = useState(0); // Renamed for clarity
  const [data, setData] = useState<ManualData | null>(null);

  // Load data
  useEffect(() => {
    setData(manualData as ManualData);
  }, []);

  if (!data) {
    return <div>Loading manual...</div>;
  }

  // Use updated keys to access step data
  const sectionsContent = [ // Renamed for clarity
    data.mediaFocusCardInstallation,
    data.driverInstallation,
    data.applicationSoftwareInstallation,
    { steps: [data.launchingApplicationPrograms] } // Treat the final string as a single step section
  ];

  const totalSections = sectionsContent.length; // Total number of installation phases/sections

  const nextSection = () => { // Renamed for clarity
    setCurrentSectionIndex((prev) => Math.min(prev + 1, totalSections - 1));
  };

  const prevSection = () => { // Renamed for clarity
    setCurrentSectionIndex((prev) => Math.max(prev - 1, 0));
  };

  // Function to handle image loading errors
  const handleImageError = (event: React.SyntheticEvent<HTMLImageElement, Event>) => {
    // Optionally hide the image or display a placeholder
    event.currentTarget.style.display = 'none';
    // You could also add a placeholder text/element here
    console.warn(`Image not found or failed to load: ${event.currentTarget.src}`);
  };

  const renderSectionContent = (sectionIndex: number) => { // Renamed for clarity
    const sectionData = sectionsContent[sectionIndex];
    const sectionKey = sectionKeys[sectionIndex]; // Get the key for filenames

    if (!sectionData) return null;

    // Don't try to render images for the final text-only section
    const isFinalSection = sectionIndex === totalSections - 1;

    return (
      <div className="step-content">
        {sectionData.warning && <p className="warning"><strong>Warning:</strong> {sectionData.warning}</p>}
        <ol>
          {sectionData.steps.map((stepText, stepIndex) => {
            // Calculate image path only if it's not the final section
            const imagePath = !isFinalSection && sectionKey
              ? `/manual_images/${sectionKey}_step_${String(stepIndex + 1).padStart(2, '0')}.png`
              : null;

            return (
              <li key={stepIndex}>
                {stepText}
                {imagePath && (
                  <img
                    src={imagePath}
                    alt={`Illustration for ${sectionKey} step ${stepIndex + 1}`}
                    className="step-image"
                    onError={handleImageError} // Add error handling
                  />
                )}
              </li>
            );
          })}
        </ol>
        {sectionData.note && <p className="note"><em>Note:</em> {sectionData.note}</p>}
      </div>
    );
  };

   const getSectionTitle = (sectionIndex: number): string => { // Renamed for clarity
    switch (sectionIndex) {
      case 0: return "Step 1: Hardware Installation";
      case 1: return "Step 2: Driver Installation";
      case 2: return "Step 3: Application Software Installation";
      case 3: return "Final: Launch Application";
      default: return `Step ${sectionIndex + 1}`;
    }
  };


  return (
    <div className="App">
      <header>
        <h1>{data.title}</h1>
      </header>

      <main>
        <section id="product-info">
          <h2>Product Information</h2>
          <div className="info-section">
            <h3>Features</h3>
            <ul>
              {data.features.map((item, index) => <li key={index}>{item}</li>)}
            </ul>
          </div>
          <div className="info-section">
            <h3>Special Features</h3>
            <ul>
              {data.specialFeatures.map((item, index) => <li key={index}>{item}</li>)}
            </ul>
          </div>
          <div className="info-section">
            <h3>System Requirements</h3>
            <ul>
              {data.systemRequirements.map((item, index) => <li key={index}>{item}</li>)}
            </ul>
          </div>
        </section>

        <section id="installation-guide">
          <h2>Installation Guide</h2>
          <div className="steps-container">
             <h3>{getSectionTitle(currentSectionIndex)}</h3>
             {renderSectionContent(currentSectionIndex)}
          </div>
          <div className="navigation-buttons">
            <button onClick={prevSection} disabled={currentSectionIndex === 0}>
              Back
            </button>
            <button onClick={nextSection} disabled={currentSectionIndex === totalSections - 1}>
              Next
            </button>
          </div>
           <div className="progress-indicator">
             Step {currentSectionIndex + 1} of {totalSections}
           </div>
        </section>
      </main>

      <footer>
        <p>Interactive Manual</p>
      </footer>
    </div>
  );
}

export default App;
