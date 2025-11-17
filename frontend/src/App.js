import React, { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import ImageUpload from './components/ImageUpload';
import SearchResults from './components/SearchResults';
import CatalogBrowser from './components/CatalogBrowser';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.jfif', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'];
const CONFIDENCE_MIN = 0.5;
const CONFIDENCE_MAX = 0.99;
const CONFIDENCE_STEP = 0.01;

const normalizeImagePath = (path = '') => {
  const normalized = path.replace(/\\/g, '/');
  if (normalized.startsWith('data/')) {
    return normalized;
  }
  if (normalized.startsWith('/')) {
    return `data${normalized}`;
  }
  return `data/${normalized}`;
};

const blobToDataUrl = (blob) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Failed to load image preview.'));
    reader.readAsDataURL(blob);
  });

function App() {
  const [rawResults, setRawResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const [backendReady, setBackendReady] = useState(false);
  const [backendAttempts, setBackendAttempts] = useState(0);
  const [backendError, setBackendError] = useState(null);
  const [backendStats, setBackendStats] = useState(null);
  const [activeView, setActiveView] = useState('search');
  const [confidence, setConfidence] = useState(0.8);
  const [sliderValue, setSliderValue] = useState(0.8);
  const confidenceInitialized = useRef(false);
  const [totalMatches, setTotalMatches] = useState(0);
  const [lastSearchConfidence, setLastSearchConfidence] = useState(0.8);
  const lastQueryFileRef = useRef(null);
  const [sliderError, setSliderError] = useState(null);
  const sliderPercent = Math.round(sliderValue * 100);
  const appliedConfidencePercent = Math.round(confidence * 100);
  const sliderDirty = Math.abs(sliderValue - confidence) > 0.0001;

  const resultsPageSize = backendStats?.results_page_size ?? DEFAULT_PAGE_SIZE;
  const maxResults = backendStats?.search_max_top_k ?? 100;
  const supportedFormats = backendStats?.supported_formats ?? DEFAULT_SUPPORTED_FORMATS;
  const minSimilarity = confidence;
  const filteredResults = useMemo(
    () => rawResults.filter((result) => result.similarity_score >= confidence),
    [rawResults, confidence]
  );
  const totalMatchesDisplay =
    typeof totalMatches === 'number' &&
    totalMatches > 0 &&
    Math.abs(confidence - lastSearchConfidence) < 0.0001
      ? totalMatches
      : filteredResults.length;

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

  useEffect(() => {
    const backendThreshold = backendStats?.search_min_similarity;
    if (
      typeof backendThreshold === 'number' &&
      !Number.isNaN(backendThreshold) &&
      !confidenceInitialized.current
    ) {
      setConfidence(backendThreshold);
      setSliderValue(backendThreshold);
      setLastSearchConfidence(backendThreshold);
      confidenceInitialized.current = true;
    }
  }, [backendStats?.search_min_similarity]);

  useEffect(() => {
    setVisibleCount((current) => {
      if (filteredResults.length === 0) {
        return 0;
      }
      if (current === 0) {
        return Math.min(resultsPageSize, filteredResults.length);
      }
      return Math.min(current, filteredResults.length);
    });
  }, [filteredResults.length, resultsPageSize]);

  const handleSearchComplete = (
    searchResults,
    imageUrl,
    totalMatchCount,
    appliedConfidence
  ) => {
    const preview = imageUrl ?? uploadedImage;
    const thresholdForCounts =
      typeof appliedConfidence === 'number' && !Number.isNaN(appliedConfidence)
        ? appliedConfidence
        : confidence;
    setRawResults(searchResults);
    setUploadedImage(preview);
    const matches = searchResults.filter(
      (result) => result.similarity_score >= thresholdForCounts
    ).length;
    setVisibleCount(matches > 0 ? Math.min(resultsPageSize, matches) : 0);
    setTotalMatches(
      typeof totalMatchCount === 'number' && !Number.isNaN(totalMatchCount)
        ? totalMatchCount
        : searchResults.length
    );
    setLastSearchConfidence(
      typeof appliedConfidence === 'number' && !Number.isNaN(appliedConfidence)
        ? appliedConfidence
        : confidence
    );
    setSliderError(null);
  };

  const handleLoadMore = () => {
    setVisibleCount((count) => Math.min(count + resultsPageSize, filteredResults.length));
  };

  const runSearchWithFile = async (file, previewDataUrl, thresholdOverride) => {
    if (!file) {
      throw new Error('Please upload an image before searching.');
    }
    const threshold =
      typeof thresholdOverride === 'number' && !Number.isNaN(thresholdOverride)
        ? thresholdOverride
        : confidence;
    lastQueryFileRef.current = file;
    setSliderError(null);
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('top_k', String(maxResults ?? 100));
      formData.append('min_similarity', String(threshold));
      const response = await axios.post(`${API_URL}/search`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      const totalMatchesHeader = Number(response.headers['x-total-matches']);
      handleSearchComplete(response.data, previewDataUrl ?? uploadedImage, totalMatchesHeader, threshold);
      requestAnimationFrame(() => {
        const root = document.querySelector('.results-container') || document.querySelector('.App-main');
        if (root) {
          root.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      });
    } catch (err) {
      console.error('Search error:', err);
      const message =
        err.response?.data?.detail || err.message || 'Search failed. Please try again.';
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  };

  const fetchProductImageForSearch = async (product) => {
    if (!product?.image_path) {
      throw new Error('Selected item has no associated image.');
    }
    const normalizedPath = normalizeImagePath(product.image_path).replace(/^data\//, '');
    const encodedPath = normalizedPath
      .split('/')
      .map((segment) => encodeURIComponent(segment))
      .join('/');
    const assetUrl = `${API_URL}/asset/${encodedPath}`;
    const response = await fetch(assetUrl);
    if (!response.ok) {
      throw new Error('Failed to download image for search.');
    }
    const blob = await response.blob();
    const extension = (product.image_path.split('.').pop() || 'jpg').split('?')[0];
    const fileName = `${product.id || 'catalog_image'}.${extension}`;
    const file = new File([blob], fileName, { type: blob.type || 'image/jpeg' });
    const dataUrl = await blobToDataUrl(blob);
    return { file, dataUrl };
  };

  const handleFindMatchesFromProduct = async (product) => {
    if (!product) return;
    setActiveView('search');
    try {
      const { file, dataUrl } = await fetchProductImageForSearch(product);
      await runSearchWithFile(file, dataUrl);
    } catch (err) {
      console.error('Find matches error:', err);
      setSliderError(err.message || 'Unable to search for this item right now.');
    }
  };

  const handleConfidenceChange = (event) => {
    setSliderValue(parseFloat(event.target.value));
  };

  const commitConfidence = () => {
    const nextValue = sliderValue;
    setConfidence((prev) => (Math.abs(prev - nextValue) < 0.0001 ? prev : nextValue));
    if (Math.abs(confidence - nextValue) <= 0.0001) {
      return;
    }
    if (!lastQueryFileRef.current || !uploadedImage) {
      setSliderError(null);
      return;
    }
    runSearchWithFile(lastQueryFileRef.current, uploadedImage, nextValue).catch((error) => {
      setSliderError(error.message);
    });
  };

  const handleConfidenceKeyUp = (event) => {
    if (
      ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End', 'Enter'].includes(
        event.key
      )
    ) {
      commitConfidence();
    }
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
            <section className="confidence-control">
              <div className="confidence-control__top">
                <div>
                  <p className="confidence-control__label">Match confidence</p>
                  <p className="confidence-control__description">
                    Hide or reveal matches by adjusting the similarity threshold.
                  </p>
                </div>
                <div className="confidence-control__value" aria-live="polite">
                  {sliderPercent}%
                  {sliderDirty && <span>pending</span>}
                </div>
              </div>
              <input
                className="confidence-control__slider"
                type="range"
                min={CONFIDENCE_MIN}
                max={CONFIDENCE_MAX}
                step={CONFIDENCE_STEP}
                value={sliderValue}
                onChange={handleConfidenceChange}
                onMouseUp={commitConfidence}
                onTouchEnd={commitConfidence}
                onKeyUp={handleConfidenceKeyUp}
                aria-label="Similarity threshold slider"
              />
              <div className="confidence-control__scale">
                <span>Lenient</span>
                <span>Strict</span>
              </div>
              {sliderDirty && (
                <p className="confidence-control__hint">Release the slider to apply</p>
              )}
              {!sliderDirty && (
                <p className="confidence-control__hint applied">
                  Showing matches at {appliedConfidencePercent}% confidence
                </p>
              )}
              {sliderError && <p className="confidence-control__error">{sliderError}</p>}
            </section>

            <ImageUpload
              onRunSearch={runSearchWithFile}
              backendReady={backendReady}
              loading={loading}
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

            {backendReady && !loading && filteredResults.length > 0 && (
              <SearchResults
                results={filteredResults}
                queryImage={uploadedImage}
                visibleCount={visibleCount}
                onLoadMore={handleLoadMore}
                minSimilarity={minSimilarity}
                totalMatches={totalMatchesDisplay}
                onFindMatches={handleFindMatchesFromProduct}
              />
            )}

            {backendReady && !loading && rawResults.length > 0 && filteredResults.length === 0 && (
              <div className="confidence-empty-state">
                <p>No matches meet the {appliedConfidencePercent}% confidence threshold.</p>
                <p>Lower the slider to review more candidates.</p>
              </div>
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
            onFindMatches={handleFindMatchesFromProduct}
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
