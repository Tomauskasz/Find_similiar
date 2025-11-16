import React, { useEffect, useState } from 'react';
import axios from 'axios';
import ImageUpload from './components/ImageUpload';
import SearchResults from './components/SearchResults';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [backendReady, setBackendReady] = useState(false);
  const [backendAttempts, setBackendAttempts] = useState(0);
  const [backendError, setBackendError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    let retryTimeout;

    const checkBackend = async (attempt = 1) => {
      if (cancelled) return;
      setBackendAttempts(attempt);
      setBackendError(null);
      try {
        await axios.get(`${API_URL}/stats`, { timeout: 3000 });
        if (!cancelled) {
          setBackendReady(true);
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
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Visual Search</h1>
        <p>Find similar products by uploading an image</p>
      </header>

      <main className="App-main">
        <ImageUpload
          onSearchComplete={handleSearchComplete}
          setLoading={setLoading}
          backendReady={backendReady}
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
          <SearchResults results={results} queryImage={uploadedImage} />
        )}
      </main>

      <footer className="App-footer">
        <p>Powered by CLIP ViT-B/32 + FAISS</p>
      </footer>
    </div>
  );
}

export default App;