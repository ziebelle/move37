import { Routes, Route, Link } from 'react-router-dom';
import ManualListPage from './ManualListPage';
import ManualViewerPage from './ManualViewerPage';
import './App.css'; // Keep some base App styles if needed, or move all to index/components

function App() {

  // App component now mainly sets up routing
  return (
    // Remove the overall .App container if all styling is handled by pages
    // Or keep it for global background/layout if desired
    // <div className="App">
      <Routes>
        <Route path="/" element={<ManualListPage />} />
        <Route path="/manuals/:manualId" element={<ManualViewerPage />} />
        {/* Optional: Add a 404 Not Found route */}
        <Route path="*" element={
          <div>
            <h2>Page Not Found</h2>
            <Link to="/">Go to Manuals List</Link>
          </div>
        } />
      </Routes>
    // </div>
  );
}

export default App;
