import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ImageUpload from './components/ImageUpload';
import SearchResults from './components/SearchResults';
import CatalogBrowser from './components/CatalogBrowser';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.jfif', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'];

function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const [backendReady, setBackendReady] = useState(false);
  const [backendAttempts, setBackendAttempts] = useState(0);
  const [backendError, setBackendError] = useState(null);
  const [backendStats, setBackendStats] = useState(null);
  const [activeView, setActiveView] = useState('search');

  const resultsPageSize = backendStats?.results_page_size ?? DEFAULT_PAGE_SIZE;
  const maxResults = backendStats?.search_max_top_k ?? 100;
  const supportedFormats = backendStats?.supported_formats ?? DEFAULT_SUPPORTED_FORMATS;
  const minSimilarity = backendStats?.search_min_similarity ?? null;

  useEffect(() => {
    let cancelled = false;
    let retryTimeout;

    const checkBackend = async (attempt = 1) => {
      if (cancelled) return;
      setBackendAttempts(attempt);
      setBackendError(null);
      try {
        const response = await axios.get(`${API_URL}/stats`, { timeout: 3000 });
        if (!cancelled) {
          setBackendReady(true);
          setBackendStats(response.data);
        }
      } catch (err) {
        if (cancelled) return;
        setBackendReady(false);
        setBackendError(err.message ?? 'Backend unavailable');
        const nextAttempt = attempt + 1;
        const delay = Math.min(5000, 1000 * nextAttempt);
        retryTimeout = setTimeout(() => checkBackend(nextAttempt), delay);
      }
    };

    checkBackend(1);

    return () => {
      cancelled = true;
      if (retryTimeout) {
        clearTimeout(retryTimeout);
      }
    };
  }, []);

  const handleSearchComplete = (searchResults, imageUrl) => {
    setResults(searchResults);
    setUploadedImage(imageUrl);
    setVisibleCount(Math.min(resultsPageSize, searchResults.length));
  };

  const handleLoadMore = () => {
    setVisibleCount((count) => Math.min(count + resultsPageSize, results.length));
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Visual Search</h1>
        <p>Find similar products by uploading an image or browse the entire catalog.</p>
        <div className="view-switcher">
          <button
            type="button"
            className={activeView === 'search' ? 'active' : ''}
            onClick={() => setActiveView('search')}
          >
            Visual Search
          </button>
          <button
            type="button"
            className={activeView === 'catalog' ? 'active' : ''}
            onClick={() => setActiveView('catalog')}
          >
            Catalog Browser
          </button>
        </div>
      </header>

      <main className="App-main">
        {activeView === 'search' && (
          <>
            <ImageUpload
              onSearchComplete={handleSearchComplete}
              setLoading={setLoading}
              backendReady={backendReady}
              maxResults={maxResults}
              supportedFormats={supportedFormats}
            />

            {!backendReady && (
              <div className="loading backend-waiting">
                <div className="spinner" />
                <p>Waiting for the backend server to start…</p>
                <p className="status-note">
                  Attempt {backendAttempts}. This page will update automatically once ready.
                </p>
                {backendError && <p className="status-note error">Last error: {backendError}</p>}
              </div>
            )}

            {backendReady && loading && (
              <div className="loading">
                <div className="spinner" />
                <p>Searching for similar items...</p>
              </div>
            )}

            {backendReady && !loading && results.length > 0 && (
              <SearchResults
                results={results}
                queryImage={uploadedImage}
                visibleCount={visibleCount}
                onLoadMore={handleLoadMore}
                minSimilarity={minSimilarity}
              />
            )}
          </>
        )}

        {activeView === 'catalog' && (
          <CatalogBrowser
            backendReady={backendReady}
            apiUrl={API_URL}
            defaultPageSize={backendStats?.catalog_default_page_size}
            maxPageSize={backendStats?.catalog_max_page_size}
            supportedFormats={supportedFormats}
          />
        )}
      </main>

      <footer className="App-footer">
        <p>Powered by CLIP ViT-B/32 + FAISS</p>
      </footer>
    </div>
  );
}

export default App;
