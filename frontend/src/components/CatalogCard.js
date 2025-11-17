import React from 'react';
import { normalizeImagePath } from '../utils/image';

const CatalogCard = ({ item, apiUrl, onSelect, onDelete }) => {
  const handleSelect = () => {
    if (typeof onSelect === 'function') {
      onSelect(item);
    }
  };

  const handleDelete = () => {
    if (typeof onDelete === 'function') {
      onDelete(item.id);
    }
  };

  return (
    <article className="catalog-card">
      <button type="button" className="catalog-card__thumb" onClick={handleSelect}>
        <img src={`${apiUrl}/${normalizeImagePath(item.image_path)}`} alt={item.name} />
      </button>
      <div className="catalog-card__meta">
        <div>
          <p className="catalog-card__name">{item.name || 'Untitled asset'}</p>
        </div>
        <button type="button" className="ghost-button danger" onClick={handleDelete}>
          Delete
        </button>
      </div>
    </article>
  );
};

export default CatalogCard;
