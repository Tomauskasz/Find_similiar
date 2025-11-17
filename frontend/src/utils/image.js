export const normalizeImagePath = (path = '') => {
  const normalized = path.replace(/\\/g, '/');
  if (normalized.startsWith('data/')) {
    return normalized;
  }
  if (normalized.startsWith('/')) {
    return `data${normalized}`;
  }
  return `data/${normalized}`;
};

export const blobToDataUrl = (blob) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Failed to load image preview.'));
    reader.readAsDataURL(blob);
  });
