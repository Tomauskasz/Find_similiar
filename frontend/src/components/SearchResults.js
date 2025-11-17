import React from 'react';
import './SearchResults.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function normalizeImagePath(product) {
  const path =
    product.image_path && product.image_path.length > 0
      ? product.image_path
      : `data/catalog/${product.id}.jpg`;

  const normalized = path.replace(/\\/g, '/');
  if (normalized.startsWith('data/')) {
    return normalized;
  }
  if (normalized.startsWith('/')) {
    return `data${normalized}`;
  }
  return `data/${normalized}`;
}

function SearchResults({ results, queryImage, visibleCount = results.length, onLoadMore }) {
  const visibleResults = results.slice(0, visibleCount);
  const canLoadMore = typeof onLoadMore === 'function' && visibleCount < results.length;

  return (
    <div className="results-container">
      <div className="results-header">
        <h2>Similar Products Found</h2>
        <p className="results-count">
          Showing {visibleResults.length} of {results.length} matches
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

            <div className="image-container">
              <img
                src={`${API_URL}/${normalizeImagePath(result.product)}`}
                alt={result.product.name}
                onError={(e) => {
                  e.target.onerror = null;
                  e.target.src = queryImage;
                }}
              />
            </div>

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

              {result.product.category && (
                <p className="category">
                  <span className="label">Category:</span> {result.product.category}
                </p>
              )}

              {result.product.price && <p className="price">${result.product.price.toFixed(2)}</p>}
            </div>
          </div>
        ))}
      </div>

      {canLoadMore && (
        <div className="load-more">
          <button type="button" onClick={onLoadMore}>
            Load more results
          </button>
        </div>
      )}
    </div>
  );
}

export default SearchResults;
