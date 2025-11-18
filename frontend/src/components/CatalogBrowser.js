import React, { useEffect, useMemo, useRef, useState } from 'react';
import './CatalogBrowser.css';
import { normalizeImagePath } from '../utils/image';
import { createApiClient } from '../services/apiClient';
import useCatalog from '../hooks/useCatalog';
import CatalogCard from './CatalogCard';
import CatalogHero from './CatalogHero';

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
  const [selectedItem, setSelectedItem] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [isPageSizeMenuOpen, setIsPageSizeMenuOpen] = useState(false);
  const [pageDisplayValue, setPageDisplayValue] = useState('');
  const [pageInputError, setPageInputError] = useState('');

  const pageSizeDropdownRef = useRef(null);
  const apiClient = useMemo(() => createApiClient(apiUrl), [apiUrl]);
  const {
    items,
    totalItems,
    totalPages,
    loading,
    error: catalogError,
    refreshCatalog,
    setErrorMessage: setCatalogError,
  } = useCatalog(apiClient, { enabled: backendReady, page, pageSize });

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

  useEffect(() => {
    if (!backendReady) {
      return;
    }
    const root = document.querySelector('.catalog-dashboard');
    if (root) {
      root.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [page, backendReady]);

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
      refreshCatalog();
    } catch (err) {
      setCatalogError(err.response?.data?.detail || 'Failed to delete catalog item.');
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
      refreshCatalog();
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
      <CatalogCard
        key={item.id}
        item={item}
        apiUrl={apiUrl}
        onSelect={setSelectedItem}
        onDelete={handleDelete}
      />
    ));
  };

  const dashboardClassName = `catalog-dashboard${isPageSizeMenuOpen ? ' dropdown-open' : ''}`;
  const modalTitleId = selectedItem ? `catalog-modal-title-${selectedItem.id}` : undefined;
  const modalDescriptionId = selectedItem ? `catalog-modal-description-${selectedItem.id}` : undefined;

  return (
    <section className={dashboardClassName}>
      <CatalogHero
        totalItems={totalItems}
        pageSize={pageSize}
        pageSizeOptions={pageSizeOptions}
        pageSizeDropdownRef={pageSizeDropdownRef}
        isPageSizeMenuOpen={isPageSizeMenuOpen}
        onTogglePageSizeMenu={() => setIsPageSizeMenuOpen((prev) => !prev)}
        onPageSizeChange={handlePageSizeChange}
        acceptedFormats={acceptedFormats}
        uploading={uploading}
        uploadError={uploadError}
        onUpload={handleUpload}
        backendReady={backendReady}
      />

      {catalogError && <div className="error-banner">{catalogError}</div>}

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
        <div
          className="catalog-modal"
          onClick={() => setSelectedItem(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby={modalTitleId}
          aria-describedby={modalDescriptionId}
        >
          <div className="catalog-modal__content" onClick={(event) => event.stopPropagation()}>
            <button type="button" className="close-modal" onClick={() => setSelectedItem(null)} aria-label="Close">
              x
            </button>
            <img src={`${apiUrl}/${normalizeImagePath(selectedItem.image_path)}`} alt={selectedItem.name} />
            <div className="modal-details" id={modalDescriptionId}>
              <h3 id={modalTitleId}>{selectedItem.name}</h3>
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
