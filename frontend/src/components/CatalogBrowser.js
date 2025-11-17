import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import './CatalogBrowser.css';
import { normalizeImagePath } from '../utils/image';
import { createApiClient } from '../services/apiClient';

const DEFAULT_PAGE_SIZE = 40;
const DEFAULT_MAX_PAGE_SIZE = 200;
const FALLBACK_FORMATS = ['.jpg', '.jpeg', '.jfif', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'];

const CatalogBrowser = ({
  backendReady,
  apiUrl,
  defaultPageSize,
  maxPageSize,
  supportedFormats,
  onFindMatches,
}) => {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize || DEFAULT_PAGE_SIZE);
  const [items, setItems] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [isUploadHover, setIsUploadHover] = useState(false);
  const [isSelectorHover, setIsSelectorHover] = useState(false);
  const [isPageSizeMenuOpen, setIsPageSizeMenuOpen] = useState(false);
  const [pageDisplayValue, setPageDisplayValue] = useState('');
  const [pageInputError, setPageInputError] = useState('');

  const pageSizeDropdownRef = useRef(null);
  const apiClient = useMemo(() => createApiClient(apiUrl), [apiUrl]);

  const effectiveMaxPageSize = maxPageSize || DEFAULT_MAX_PAGE_SIZE;
  const acceptedFormats = supportedFormats?.length ? supportedFormats : FALLBACK_FORMATS;

  useEffect(() => {
    setPageSize(defaultPageSize || DEFAULT_PAGE_SIZE);
    setPage(1);
  }, [defaultPageSize]);

  useEffect(() => {
    if (totalPages === 0) {
      setPageDisplayValue('');
    } else {
      setPageDisplayValue(String(page));
    }
  }, [page, totalPages]);

  const fetchCatalog = useCallback(async () => {
    if (!backendReady) return;
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/catalog/items', {
        params: { page, page_size: pageSize },
      });
      setItems(response.data.items || []);
      setTotalItems(response.data.total_items || 0);
      setTotalPages(response.data.total_pages || 0);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load catalog.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [apiClient, backendReady, page, pageSize]);

  useEffect(() => {
    fetchCatalog();
  }, [fetchCatalog]);

  useEffect(() => {
    const root = document.querySelector('.catalog-dashboard');
    if (root) {
      root.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [page]);

  useEffect(() => {
    if (!isPageSizeMenuOpen) {
      return undefined;
    }
    const handleClickOutside = (event) => {
      if (pageSizeDropdownRef.current && !pageSizeDropdownRef.current.contains(event.target)) {
        setIsPageSizeMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isPageSizeMenuOpen]);

  const handlePageSizeChange = (value) => {
    if (Number.isNaN(value)) return;
    const normalized = Math.min(Math.max(1, value), effectiveMaxPageSize);
    setPageSize(normalized);
    setPage(1);
    setIsPageSizeMenuOpen(false);
  };

  const handlePrevPage = () => setPage((current) => Math.max(1, current - 1));

  const handleNextPage = () => {
    if (totalPages === 0) return;
    setPage((current) => Math.min(totalPages, current + 1));
  };

  const handlePageInputChange = (event) => {
    setPageInputError('');
    setPageDisplayValue(event.target.value);
  };

  const applyPageInput = () => {
    if (!totalPages) {
      setPageInputError('Catalog is empty.');
      return;
    }
    const value = Number(pageDisplayValue);
    if (!Number.isInteger(value) || value < 1 || value > totalPages) {
      setPageInputError(`Enter a value between 1 and ${totalPages}.`);
      return;
    }
    setPage(value);
    setPageDisplayValue(String(value));
  };

  const handlePageInputSubmit = (event) => {
    event.preventDefault();
    applyPageInput();
  };

  const handlePageInputBlur = () => {
    if (totalPages > 0) {
      setPageDisplayValue(String(page));
    } else {
      setPageDisplayValue('');
    }
  };

  const handleDelete = async (productId) => {
    const confirmed = window.confirm('Delete this catalog image? This action cannot be undone.');
    if (!confirmed) return;
    try {
      await apiClient.delete(`/catalog/${productId}`);
      setPage((currentPage) => {
        if (items.length === 1 && currentPage > 1) {
          return currentPage - 1;
        }
        return currentPage;
      });
      fetchCatalog();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete catalog item.');
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      await apiClient.post('/add-product', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      event.target.value = '';
      setPage(1);
      fetchCatalog();
    } catch (err) {
      setUploadError(err.response?.data?.detail || 'Failed to upload image.');
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  const pageSizeOptions = useMemo(() => {
    const baseOptions = [20, 40, 80, 120, 160, 200];
    const filtered = baseOptions.filter((opt) => opt <= effectiveMaxPageSize);
    if (!filtered.includes(effectiveMaxPageSize)) {
      filtered.push(effectiveMaxPageSize);
    }
    const unique = Array.from(new Set([...filtered, pageSize])).sort((a, b) => a - b);
    return unique;
  }, [effectiveMaxPageSize, pageSize]);

  const renderCards = () => {
    if (loading) {
      return <div className="loading-panel">Loading catalog...</div>;
    }
    if (items.length === 0) {
      return (
        <div className="empty-state">
          <p>No catalog entries yet.</p>
          <p>Use "Add to catalog" to start populating the gallery.</p>
        </div>
      );
    }
    return items.map((item) => (
      <article key={item.id} className="catalog-card">
        <button type="button" className="catalog-card__thumb" onClick={() => setSelectedItem(item)}>
          <img src={`${apiUrl}/${normalizeImagePath(item.image_path)}`} alt={item.name} />
        </button>
        <div className="catalog-card__meta">
          <div>
            <p className="catalog-card__name">{item.name || 'Untitled asset'}</p>
          </div>
          <button type="button" className="ghost-button danger" onClick={() => handleDelete(item.id)}>
            Delete
          </button>
        </div>
      </article>
    ));
  };

  const dashboardClassName = `catalog-dashboard${isPageSizeMenuOpen ? ' dropdown-open' : ''}`;

  return (
    <section className={dashboardClassName}>
      <div className="catalog-hero">
        <div className="catalog-hero__stats">
          <div className="stat-card stat-card--hoverable">
            <span>Total items</span>
            <strong>{totalItems}</strong>
          </div>
          <div className={`stat-card stat-card--selector${isSelectorHover ? ' hover-active' : ''}`}>
            <span className="stat-card__label">Images per page</span>
            <div
              className={`page-size-dropdown ${isPageSizeMenuOpen ? 'open' : ''}`}
              ref={pageSizeDropdownRef}
            >
              <button
                type="button"
                className="page-size-dropdown__toggle"
                onClick={() => setIsPageSizeMenuOpen((prev) => !prev)}
                aria-haspopup="listbox"
                aria-expanded={isPageSizeMenuOpen}
                onMouseEnter={() => setIsSelectorHover(true)}
                onMouseLeave={() => setIsSelectorHover(false)}
              >
                <span className="page-size-dropdown__value">{pageSize}</span>
                <span className="page-size-dropdown__chevron" aria-hidden="true" />
              </button>
              {isPageSizeMenuOpen && (
                <div className="page-size-dropdown__menu" role="listbox" aria-label="Select images per page">
                  {pageSizeOptions.map((option) => (
                    <button
                      type="button"
                      key={option}
                      className={`page-size-dropdown__option ${option === pageSize ? 'active' : ''}`}
                      onClick={() => handlePageSizeChange(option)}
                      role="option"
                      aria-selected={option === pageSize}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className={`stat-card stat-card--upload${isUploadHover ? ' hover-active' : ''}`}>
            <label
              className="upload-chip upload-chip--stretch"
              onMouseEnter={() => setIsUploadHover(true)}
              onMouseLeave={() => setIsUploadHover(false)}
            >
              <input
                type="file"
                accept={acceptedFormats.join(',')}
                onChange={handleUpload}
                disabled={!backendReady || uploading}
              />
              <span>{uploading ? 'Uploading...' : 'Add to catalog'}</span>
            </label>
            <p className="hint">
              Accepted: {acceptedFormats.map((ext) => ext.replace('.', '').toUpperCase()).join(', ')}
            </p>
            {uploadError && <p className="field-error">{uploadError}</p>}
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="catalog-grid">{renderCards()}</div>
      <div className="catalog-pagination-bar">
        <button type="button" onClick={handlePrevPage} disabled={page <= 1}>
          Previous
        </button>
        <form className="catalog-page-display" onSubmit={handlePageInputSubmit}>
          <span>Page</span>
          <input
            type="number"
            min="1"
            max={totalPages || 1}
            value={pageDisplayValue}
            onChange={handlePageInputChange}
            onBlur={handlePageInputBlur}
            disabled={totalPages === 0}
          />
          <span>of {totalPages}</span>
        </form>
        <button type="button" onClick={handleNextPage} disabled={totalPages === 0 || page >= totalPages}>
          Next
        </button>
      </div>
      {pageInputError && <p className="page-input-error">{pageInputError}</p>}

      {selectedItem && (
        <div className="catalog-modal" onClick={() => setSelectedItem(null)} role="presentation">
          <div className="catalog-modal__content" onClick={(event) => event.stopPropagation()}>
            <button type="button" className="close-modal" onClick={() => setSelectedItem(null)} aria-label="Close">
              x
            </button>
            <img src={`${apiUrl}/${normalizeImagePath(selectedItem.image_path)}`} alt={selectedItem.name} />
            <div className="modal-details">
              <h3>{selectedItem.name}</h3>
              {selectedItem.category && (
                <p className="modal-meta">
                  <span>{selectedItem.category}</span>
                </p>
              )}
              {typeof onFindMatches === 'function' && (
                <button
                  type="button"
                  className="find-matches-button"
                  onClick={() => {
                    onFindMatches(selectedItem);
                    setSelectedItem(null);
                  }}
                >
                  Find matches
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default CatalogBrowser;
