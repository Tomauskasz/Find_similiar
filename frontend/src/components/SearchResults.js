import React, { useState } from 'react';
import './SearchResults.css';
import { normalizeImagePath } from '../utils/image';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const getProductImagePath = (product) => {
  const fallback = `data/catalog/${product.id}.jpg`;
  return normalizeImagePath(product.image_path && product.image_path.length > 0 ? product.image_path : fallback);
};

function SearchResults({
  results,
  queryImage,
  visibleCount = results.length,
  onLoadMore,
  minSimilarity,
  totalMatches,
  onFindMatches,
}) {
  const [selectedResult, setSelectedResult] = useState(null);
  const modalTitleId = selectedResult ? `result-modal-title-${selectedResult.product.id}` : undefined;
  const modalDescriptionId = selectedResult ? `result-modal-description-${selectedResult.product.id}` : undefined;
  const totalResults = results.length;
  const totalLabelCount =
    typeof totalMatches === 'number' && !Number.isNaN(totalMatches) ? totalMatches : totalResults;
  const displayCount = Math.min(visibleCount, totalResults);
  const visibleResults = results.slice(0, displayCount);
  const canLoadMore = typeof onLoadMore === 'function' && displayCount < totalResults;

  return (
    <div className="results-container">
      <div className="results-header">
        <h2>Similar Products Found</h2>
        <p className="results-count">
          Showing {displayCount} of {totalLabelCount} matches
          {typeof minSimilarity === 'number' && (
            <span className="match-threshold">>= {(minSimilarity * 100).toFixed(0)}% match</span>
          )}
        </p>
      </div>

      <div className="query-section">
        <h3>Your Search Image</h3>
        <img src={queryImage} alt="Query" className="query-image" />
      </div>

      <div className="results-grid">
        {visibleResults.map((result, index) => (
          <div key={result.product.id} className="result-card">
            <div className="rank-badge">{index + 1}</div>

            <button
              type="button"
              className="image-container result-card__thumb"
              onClick={() => setSelectedResult(result)}
            >
              <img
                src={`${API_URL}/${getProductImagePath(result.product)}`}
                alt={result.product.name}
                onError={(e) => {
                  e.target.onerror = null;
                  e.target.src = queryImage;
                }}
              />
            </button>

            <div className="card-content">
              <h3 className="product-name">{result.product.name}</h3>

              <div className="similarity-bar">
                <div className="similarity-label">
                  <span>Match</span>
                  <span className="score">{(result.similarity_score * 100).toFixed(1)}%</span>
                </div>
                <div className="bar-background">
                  <div className="bar-fill" style={{ width: `${result.similarity_score * 100}%` }} />
                </div>
              </div>

            </div>
          </div>
        ))}
      </div>

      {canLoadMore && (
        <div className="load-more">
          <button type="button" onClick={onLoadMore}>
            Show more results
          </button>
        </div>
      )}

      {selectedResult && (
        <div
          className="catalog-modal"
          onClick={() => setSelectedResult(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby={modalTitleId}
          aria-describedby={modalDescriptionId}
        >
          <div className="catalog-modal__content" onClick={(event) => event.stopPropagation()}>
            <button
              type="button"
              className="close-modal"
              onClick={() => setSelectedResult(null)}
              aria-label="Close"
            >
              x
            </button>
            <img
              src={`${API_URL}/${getProductImagePath(selectedResult.product)}`}
              alt={selectedResult.product.name}
            />
            <div className="modal-details" id={modalDescriptionId}>
              <h3 id={modalTitleId}>{selectedResult.product.name}</h3>
              <p>Similarity: {(selectedResult.similarity_score * 100).toFixed(1)}%</p>
              {typeof onFindMatches === 'function' && (
                <button
                  type="button"
                  className="find-matches-button"
                  onClick={() => {
                    onFindMatches(selectedResult.product);
                    setSelectedResult(null);
                  }}
                >
                  Find matches
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SearchResults;


