import React, { useMemo, useState } from 'react';

const CatalogHero = ({
  totalItems,
  pageSize,
  pageSizeOptions,
  pageSizeDropdownRef,
  isPageSizeMenuOpen,
  onTogglePageSizeMenu,
  onPageSizeChange,
  acceptedFormats,
  uploading,
  uploadError,
  onUpload,
  backendReady,
}) => {
  const [isSelectorHover, setIsSelectorHover] = useState(false);
  const [isUploadHover, setIsUploadHover] = useState(false);
  const uploadHintId = useMemo(() => 'catalog-upload-hint', []);
  const uploadErrorId = useMemo(() => 'catalog-upload-error', []);
  const uploadDescribedBy = uploadError ? `${uploadHintId} ${uploadErrorId}` : uploadHintId;

  return (
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
              onClick={onTogglePageSizeMenu}
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
                    onClick={() => onPageSizeChange(option)}
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
            aria-label="Add a product to the catalog"
          >
            <input
              type="file"
              accept={acceptedFormats.join(',')}
              onChange={onUpload}
              disabled={!backendReady || uploading}
              aria-describedby={uploadDescribedBy}
            />
            <span className="upload-chip__label">{uploading ? 'Uploading...' : 'Add to catalog'}</span>
          </label>
          <p className="catalog-upload__hint" id={uploadHintId}>
            Accepted: {acceptedFormats.map((ext) => ext.replace('.', '').toUpperCase()).join(', ')}
          </p>
          {uploadError && (
            <p className="catalog-upload__error" id={uploadErrorId} aria-live="polite">
              {uploadError}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default CatalogHero;
