import React, { useCallback, useMemo, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import './ImageUpload.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const FALLBACK_FORMATS = ['.jpg', '.jpeg', '.jfif', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'];

const UploadGlyph = ({ variant = 'ready' }) => (
  <div className={`upload-icon upload-icon--${variant}`} aria-hidden="true">
    <svg viewBox="0 0 64 64" role="presentation" focusable="false">
      <polyline points="22 30 32 20 42 30" />
      <line x1="32" y1="20" x2="32" y2="46" />
      <rect x="20" y="46" width="24" height="6" rx="3" />
    </svg>
  </div>
);

function ImageUpload({ onSearchComplete, setLoading, backendReady, maxResults, supportedFormats }) {
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const acceptedFormats = supportedFormats && supportedFormats.length > 0 ? supportedFormats : FALLBACK_FORMATS;
  const formatDisplay = useMemo(
    () => acceptedFormats.map((fmt) => fmt.replace('.', '').toUpperCase()).join(', '),
    [acceptedFormats]
  );

  const onDrop = useCallback(
    async (acceptedFiles) => {
      if (!backendReady) {
        setError('Backend is still starting up. Please wait a moment and try again.');
        return;
      }

      const file = acceptedFiles[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = () => setPreview(reader.result);
      reader.readAsDataURL(file);

      setLoading(true);
      setError(null);

      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('top_k', String(maxResults ?? 100));

        const response = await axios.post(`${API_URL}/search`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });

        onSearchComplete(response.data, reader.result);
      } catch (err) {
        if (err.response?.status === 415) {
          setError(err.response?.data?.detail || `Unsupported file format. Supported formats: ${formatDisplay}.`);
        } else {
          setError(err.response?.data?.detail || 'Search failed. Please try again.');
        }
        console.error('Search error:', err);
      } finally {
        setLoading(false);
      }
    },
    [backendReady, onSearchComplete, setLoading, maxResults, formatDisplay]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': acceptedFormats,
    },
    multiple: false,
  });

  return (
    <div className="upload-container">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''}`}
        style={{ pointerEvents: backendReady ? 'auto' : 'none', opacity: backendReady ? 1 : 0.6 }}
      >
        <input {...getInputProps()} />

        {!backendReady ? (
          <div className="upload-prompt">
            <UploadGlyph variant="waiting" />
            <h3>Backend warming up...</h3>
            <p>Please wait while the server finishes starting.</p>
          </div>
        ) : preview ? (
          <div className="preview">
            <img src={preview} alt="Upload preview" />
            <p className="upload-hint">Drop another image or click to change</p>
          </div>
        ) : (
          <div className="upload-prompt">
            <UploadGlyph />
            <h3>Upload Product Image</h3>
            <p>{isDragActive ? 'Drop image here...' : 'Drag & drop or click to select'}</p>
            <p className="file-types">Supports: {formatDisplay}</p>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          <span aria-hidden>[!]</span> {error}
        </div>
      )}
    </div>
  );
}

export default ImageUpload;
