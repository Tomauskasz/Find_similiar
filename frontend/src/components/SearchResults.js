import React from 'react';
import './SearchResults.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function SearchResults({ results, queryImage }) {
  return (
    <div className="results-container">
      <div className="results-header">
        <h2>Similar Products Found</h2>
        <p className="results-count">{results.length} matches</p>
      </div>

      <div className="query-section">
        <h3>Your Search Image</h3>
        <img src={queryImage} alt="Query" className="query-image" />
      </div>

      <div className="results-grid">
        {results.map((result, index) => (
          <div key={result.product.id} className="result-card">
            <div className="rank-badge">{index + 1}</div>
            
            <div className="image-container">
              <img
                src={`${API_URL}/${result.product.image_path}`}
                alt={result.product.name}
                onError={(e) => {
                  e.target.onerror = null;
                  e.target.src = queryImage; // Fallback
                }}
              />
            </div>
            
            <div className="card-content">
              <h3 className="product-name">{result.product.name}</h3>
              
              <div className="similarity-bar">
                <div className="similarity-label">
                  <span>Match</span>
                  <span className="score">
                    {(result.similarity_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="bar-background">
                  <div
                    className="bar-fill"
                    style={{ width: `${result.similarity_score * 100}%` }}
                  />
                </div>
              </div>
              
              {result.product.category && (
                <p className="category">
                  <span className="label">Category:</span> {result.product.category}
                </p>
              )}
              
              {result.product.price && (
                <p className="price">${result.product.price.toFixed(2)}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default SearchResults;