import React, { useState } from 'react';
import ImageUpload from './components/ImageUpload';
import SearchResults from './components/SearchResults';
import './App.css';

function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);

  const handleSearchComplete = (searchResults, imageUrl) => {
    setResults(searchResults);
    setUploadedImage(imageUrl);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🔍 Visual Search</h1>
        <p>Find similar products by uploading an image</p>
      </header>
      
      <main className="App-main">
        <ImageUpload 
          onSearchComplete={handleSearchComplete}
          setLoading={setLoading}
        />
        
        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Searching for similar items...</p>
          </div>
        )}
        
        {!loading && results.length > 0 && (
          <SearchResults 
            results={results} 
            queryImage={uploadedImage}
          />
        )}
      </main>
      
      <footer className="App-footer">
        <p>Powered by AI • ResNet50 + FAISS</p>
      </footer>
    </div>
  );
}

export default App;