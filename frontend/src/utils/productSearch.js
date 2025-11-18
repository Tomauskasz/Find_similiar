import { blobToDataUrl, normalizeImagePath } from './image';

export function buildAssetUrl(apiUrl, imagePath) {
  const normalizedPath = normalizeImagePath(imagePath).replace(/^data\//, '');
  const encodedPath = normalizedPath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  return `${apiUrl}/asset/${encodedPath}`;
}

export async function fetchProductImageForSearch(product, apiUrl) {
  if (!product?.image_path) {
    throw new Error('Selected item has no associated image.');
  }

  const assetUrl = buildAssetUrl(apiUrl, product.image_path);
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
}

export function scrollResultsIntoView() {
  requestAnimationFrame(() => {
    const root = document.querySelector('.results-container') || document.querySelector('.App-main');
    if (root) {
      root.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  });
}
