import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ImageUpload from './components/ImageUpload';
import SearchResults from './components/SearchResults';
import CatalogBrowser from './components/CatalogBrowser';
import useBackendStats from './hooks/useBackendStats';
import useConfidence from './hooks/useConfidence';
import useCatalogView from './hooks/useCatalogView';
import useSearchResults from './hooks/useSearchResults';
import { buildAssetUrl, fetchProductImageForSearch, scrollResultsIntoView } from './utils/productSearch';
import { createApiClient, searchSimilar } from './services/apiClient';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.jfif', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'];
const CONFIDENCE_MIN = 0.5;
const CONFIDENCE_MAX = 0.99;
const CONFIDENCE_STEP = 0.01;

function App() {
  const [loading, setLoading] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);
  const memoizedClient = useMemo(() => createApiClient(API_URL), []);
  const { backendReady, backendStats, backendAttempts, backendError } = useBackendStats(memoizedClient);
  const [activeView, selectView] = useCatalogView('search');
  const {
    confidence,
    sliderValue,
    sliderPercent,
    appliedConfidencePercent,
    sliderDirty,
    lastSearchConfidence,
    handleSliderChange,
    commitSlider,
    markSearchConfidence,
    syncBackendConfidence,
  } = useConfidence(0.8);
  const confidenceInitialized = useRef(false);
  const lastQueryFileRef = useRef(null);
  const [sliderError, setSliderError] = useState(null);
  const {
    rawResults,
    setRawResults,
    getFilteredResults,
    visibleCount,
    setVisibleCount,
    totalMatches,
    setTotalMatches,
    loadMore,
  } = useSearchResults();

  const resultsPageSize = backendStats?.results_page_size ?? DEFAULT_PAGE_SIZE;
  const maxResults = backendStats?.total_products ?? Number.MAX_SAFE_INTEGER;
  const supportedFormats = backendStats?.supported_formats ?? DEFAULT_SUPPORTED_FORMATS;
  const minSimilarity = confidence;
  const filteredResultsList = useMemo(() => getFilteredResults(confidence), [getFilteredResults, confidence]);
  const totalMatchesDisplay =
    typeof totalMatches === 'number' &&
    totalMatches > 0 &&
    Math.abs(confidence - lastSearchConfidence) < 0.0001
      ? totalMatches
      : filteredResultsList.length;

  useEffect(() => {
    const backendThreshold = backendStats?.search_min_similarity;
    if (
      typeof backendThreshold === 'number' &&
      !Number.isNaN(backendThreshold) &&
      !confidenceInitialized.current
    ) {
      syncBackendConfidence(backendThreshold);
      confidenceInitialized.current = true;
    }
  }, [backendStats?.search_min_similarity, syncBackendConfidence]);

  useEffect(() => {
    setVisibleCount((current) => {
      if (filteredResultsList.length === 0) {
        return 0;
      }
      if (current === 0) {
        return Math.min(resultsPageSize, filteredResultsList.length);
      }
      return Math.min(current, filteredResultsList.length);
    });
  }, [filteredResultsList.length, resultsPageSize, setVisibleCount]);

  const handleSearchComplete = useCallback(
    (searchResults, imageUrl, totalMatchCount, appliedConfidence) => {
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
      markSearchConfidence(thresholdForCounts);
      setSliderError(null);
    },
    [uploadedImage, confidence, resultsPageSize, markSearchConfidence, setRawResults, setVisibleCount, setTotalMatches]
  );

  const handleLoadMore = () => {
    loadMore(resultsPageSize, confidence);
  };

  const runSearchWithFile = useCallback(async (file, previewDataUrl, options = {}) => {
    const { thresholdOverride, excludeProductId } = options;
    if (!file) {
      throw new Error('Please upload an image before searching.');
    }
    const threshold =
      typeof thresholdOverride === 'number' && !Number.isNaN(thresholdOverride)
        ? thresholdOverride
        : confidence;
    lastQueryFileRef.current = file;
    if (typeof previewDataUrl === 'string' && previewDataUrl.length > 0) {
      setUploadedImage(previewDataUrl);
    }
    setSliderError(null);
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('top_k', String(maxResults ?? 100));
      formData.append('min_similarity', String(threshold));
      const response = await searchSimilar(memoizedClient, formData);
      const totalMatchesHeader = Number(response.headers['x-total-matches']);
      const rawResults = response.data || [];
      const filteredResults =
        excludeProductId != null
          ? rawResults.filter(
              (result) => result?.product?.id !== excludeProductId
            )
          : rawResults;
      const removedCount = rawResults.length - filteredResults.length;
      const adjustedTotalMatches = Number.isFinite(totalMatchesHeader)
        ? Math.max(0, totalMatchesHeader - removedCount)
        : undefined;
      handleSearchComplete(
        filteredResults,
        previewDataUrl ?? uploadedImage,
        adjustedTotalMatches,
        threshold
      );
      scrollResultsIntoView();
    } catch (err) {
      console.error('Search error:', err);
      const message =
        err.response?.data?.detail || err.message || 'Search failed. Please try again.';
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  }, [memoizedClient, confidence, maxResults, uploadedImage, handleSearchComplete]);

  const handleFindMatchesFromProduct = async (product) => {
    if (!product) return;
    selectView('search');
    if (product.image_path) {
      const assetUrl = buildAssetUrl(API_URL, product.image_path);
      setUploadedImage(assetUrl);
    }
    try {
      const { file, dataUrl } = await fetchProductImageForSearch(product, API_URL);
      await runSearchWithFile(file, dataUrl, { excludeProductId: product.id });
    } catch (err) {
      console.error('Find matches error:', err);
      setSliderError(err.message || 'Unable to search for this item right now.');
    }
  };

  const handleConfidenceChange = handleSliderChange;

  const commitConfidence = () => {
    const previous = confidence;
    commitSlider();
    const nextValue = sliderValue;
    if (Math.abs(previous - nextValue) <= 0.0001) {
      return;
    }
    if (!lastQueryFileRef.current || !uploadedImage) {
      setSliderError(null);
      return;
    }
    runSearchWithFile(lastQueryFileRef.current, uploadedImage, { thresholdOverride: nextValue }).catch((error) => {
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
            onClick={() => selectView('search')}
          >
            Visual Search
          </button>
          <button
            type="button"
            className={activeView === 'catalog' ? 'active' : ''}
            onClick={() => selectView('catalog')}
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
              previewImage={uploadedImage}
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

            {backendReady && !loading && filteredResultsList.length > 0 && (
              <SearchResults
                results={filteredResultsList}
                queryImage={uploadedImage}
                visibleCount={visibleCount}
                onLoadMore={handleLoadMore}
                minSimilarity={minSimilarity}
                totalMatches={totalMatchesDisplay}
                onFindMatches={handleFindMatchesFromProduct}
              />
            )}

            {backendReady && !loading && rawResults.length > 0 && filteredResultsList.length === 0 && (
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
