import React, { useState } from 'react';

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
          >
            <input
              type="file"
              accept={acceptedFormats.join(',')}
              onChange={onUpload}
              disabled={!backendReady || uploading}
            />
            <span>{uploading ? 'Uploading...' : 'Add to catalog'}</span>
          </label>
          <p className="hint">Accepted: {acceptedFormats.map((ext) => ext.replace('.', '').toUpperCase()).join(', ')}</p>
          {uploadError && <p className="field-error">{uploadError}</p>}
        </div>
      </div>
    </div>
  );
};

export default CatalogHero;
