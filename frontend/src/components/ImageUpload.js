import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import './ImageUpload.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function ImageUpload({ onSearchComplete, setLoading }) {
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    // Create preview
    const reader = new FileReader();
    reader.onload = () => setPreview(reader.result);
    reader.readAsDataURL(file);

    // Upload and search
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('top_k', '12');

      const response = await axios.post(
        `${API_URL}/search`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      onSearchComplete(response.data, reader.result);
    } catch (err) {
      setError(err.response?.data?.detail || 'Search failed. Please try again.');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  }, [onSearchComplete, setLoading]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
    },
    multiple: false,
  });

  return (
    <div className="upload-container">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''}`}
      >
        <input {...getInputProps()} />
        
        {preview ? (
          <div className="preview">
            <img src={preview} alt="Upload preview" />
            <p className="upload-hint">Drop another image or click to change</p>
          </div>
        ) : (
          <div className="upload-prompt">
            <div className="upload-icon">📸</div>
            <h3>Upload Product Image</h3>
            <p>
              {isDragActive
                ? "Drop image here..."
                : "Drag & drop an image, or click to select"}
            </p>
            <p className="file-types">Supports: JPG, PNG, GIF, BMP</p>
          </div>
        )}
      </div>
      
      {error && (
        <div className="error-message">
          <span>⚠️</span> {error}
        </div>
      )}
    </div>
  );
}

export default ImageUpload;