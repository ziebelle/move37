import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import './ManualListPage.css'; // We'll create this CSS file next

// --- API Configuration ---
const API_BASE_URL = 'http://localhost:5001'; // Adjust if needed
// --- End API Configuration ---

interface ManualListItem {
    manual_id: number;
    title: string;
    source_path: string;
}

function ManualListPage() {
    const [manuals, setManuals] = useState<ManualListItem[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true); // Keep loading state
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState<string>('');
    const [hasSearched, setHasSearched] = useState<boolean>(false); // Track if user has typed

    // Fetch all manuals initially, but don't display until search
    useEffect(() => {
        const fetchManuals = async () => {
            setIsLoading(true);
            setError(null);
            try {
                const response = await fetch(`${API_BASE_URL}/api/manuals`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data: ManualListItem[] = await response.json();
                setManuals(data);
            } catch (e) {
                console.error("Failed to fetch manuals list:", e);
                setError(e instanceof Error ? e.message : "An unknown error occurred");
            } finally {
                setIsLoading(false);
            }
        };

        fetchManuals();
    }, []); // Run only once on mount

    const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchTerm(e.target.value);
        setHasSearched(true); // Mark that a search has been attempted
    };

    const filteredManuals = useMemo(() => {
        // Only filter if a search term exists
        if (!searchTerm) {
            return []; // Return empty array if no search term
        }
        return manuals.filter(manual =>
            manual.title.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }, [manuals, searchTerm]);

    return (
        <div className="manual-list-page">
            {/* Center content container */}
            <div className="list-content-centered">
                <h1>TechniSat Manuals</h1>

                <div className="search-container">
                    <input
                        type="text"
                        placeholder="Enter manual title..."
                        value={searchTerm}
                        onChange={handleSearchChange} // Use handler
                        className="search-input"
                        autoFocus // Focus on load
                    />
                </div>

                {isLoading && <div className="loading-message">Loading available manuals...</div>}
                {error && <div className="error-message">Error loading manuals: {error}</div>}

                {/* Only show results container if not loading, no error, AND a search has been initiated */}
                {!isLoading && !error && hasSearched && (
                    <div className="results-container">
                        {searchTerm && ( // Only show list if there's a search term
                            <ul className="manual-list">
                                {filteredManuals.length > 0 ? (
                                    filteredManuals.map(manual => (
                                        <li key={manual.manual_id} className="manual-list-item">
                                            <Link to={`/manuals/${manual.manual_id}`}>
                                                {manual.title}
                                            </Link>
                                            {/* Optional: Show source path if needed */}
                                            {/* <span className="manual-source">({manual.source_path})</span> */}
                                        </li>
                                    ))
                                ) : (
                                    <li className="no-results">No manuals found matching '{searchTerm}'.</li>
                                )}
                            </ul>
                        )}
                        {!searchTerm && ( // Show prompt if search term is cleared after searching
                             <p className="search-prompt">Enter a title to search for manuals.</p>
                        )}
                    </div>
                )}
                 {/* Initial prompt before any search */}
                 {!isLoading && !error && !hasSearched && (
                     <p className="search-prompt">Enter a title to search for manuals.</p>
                 )}
            </div>
        </div>
    );
}

export default ManualListPage;