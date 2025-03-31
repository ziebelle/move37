import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import './ManualListPage.css';

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
    const [isLoadingList, setIsLoadingList] = useState<boolean>(false);
    const [listError, setListError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState<string>('');
    const [hasSearched, setHasSearched] = useState<boolean>(false);
    const [qaQuestion, setQaQuestion] = useState<string>('');
    const [qaAnswer, setQaAnswer] = useState<string | null>(null);
    const [isQaLoading, setIsQaLoading] = useState<boolean>(false);
    const [qaError, setQaError] = useState<string | null>(null);

    // Fetch manuals list (optional)
    useEffect(() => {
        const fetchManuals = async () => {
            setIsLoadingList(true); setListError(null);
            try {
                const response = await fetch(`${API_BASE_URL}/api/manuals`);
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                const data: ManualListItem[] = await response.json();
                setManuals(data);
            } catch (e) {
                console.error("Failed to fetch manuals list:", e);
                setListError(e instanceof Error ? e.message : "An unknown error occurred");
            } finally { setIsLoadingList(false); }
        };
        fetchManuals();
    }, []);

    const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchTerm(e.target.value); setHasSearched(true);
    };

    const filteredManuals = useMemo(() => {
        if (!searchTerm) return [];
        return manuals.filter(manual => manual.title.toLowerCase().includes(searchTerm.toLowerCase()));
    }, [manuals, searchTerm]);

    const handleQaSubmit = async (event: React.FormEvent) => {
        event.preventDefault(); if (!qaQuestion.trim()) return;
        setIsQaLoading(true); setQaError(null); setQaAnswer(null);
        try {
            const response = await fetch(`${API_BASE_URL}/api/qa`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: qaQuestion }),
            });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json(); setQaAnswer(data.answer);
        } catch (e) {
            console.error("Failed to get QA answer:", e);
            setQaError(e instanceof Error ? e.message : "An unknown error occurred");
        } finally { setIsQaLoading(false); }
    };

    return (
        // Apply full height and flex direction to the main page container
        <div className="manual-list-page">
            <h1 style={{ marginBottom: '60px', marginTop: '100px' }}>TechniSat SUPPORT</h1>

            {/* Container for the two columns */}
            <div className="main-content-columns">

                {/* Left Column: Search Section (1/3 width) */}
                <div className="search-section column">
                    <h2>Search by Title</h2>
                    <div className="search-container">
                        <input
                            type="text"
                            placeholder="Enter manual title..."
                            value={searchTerm}
                            onChange={handleSearchChange}
                            className="search-input"
                            autoFocus
                        />
                    </div>
                    {/* Search Results Area */}
                    <div className="results-area">
                        {isLoadingList && <div className="loading-message">Loading list...</div>}
                        {listError && <div className="error-message">Error: {listError}</div>}
                        {!isLoadingList && !listError && hasSearched && (
                            <>
                                {searchTerm ? (
                                    <ul className="manual-list">
                                        {filteredManuals.length > 0 ? (
                                            filteredManuals.map(manual => (
                                                <li key={manual.manual_id} className="manual-list-item">
                                                    <Link to={`/manuals/${manual.manual_id}`}>{manual.title}</Link>
                                                </li>
                                            ))
                                        ) : ( <li className="no-results">No matches found.</li> )}
                                    </ul>
                                ) : ( <p className="search-prompt">Enter title to search.</p> )}
                            </>
                        )}
                        {!isLoadingList && !listError && !hasSearched && (
                             <p className="search-prompt">Enter title to search.</p>
                         )}
                     </div>
                </div>

                {/* Right Column: QA Section (2/3 width) */}
                <div className="qa-container column">
                    <h2>Ask a Question</h2>
                    <form onSubmit={handleQaSubmit} className="qa-form">
                        <textarea
                            placeholder="Ask anything about the manuals..."
                            value={qaQuestion}
                            onChange={(e) => setQaQuestion(e.target.value)}
                            className="qa-input"
                            rows={4}
                        />
                        <button type="submit" disabled={isQaLoading || !qaQuestion.trim()} className="qa-submit-button">
                            {isQaLoading ? 'Asking...' : 'Ask'}
                        </button>
                    </form>
                    {/* QA Results Area */}
                    <div className="qa-results-area">
                        {isQaLoading && (
                            <div className="gemini-loader">
                                <div></div><div></div><div></div>
                            </div>
                        )}
                        {qaError && <div className="error-message">Error: {qaError}</div>}
                        {qaAnswer && (
                            <div className="qa-answer">
                                <h3>Answer:</h3>
                                <p>{qaAnswer}</p>
                            </div>
                        )}
                    </div>
                </div>

            </div> {/* End main-content-columns */}
        </div>
    );
}

export default ManualListPage;