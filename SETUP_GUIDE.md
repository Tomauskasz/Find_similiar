# 🎯 Visual Search Setup Guide

Follow these steps to get your Visual Search AI service up and running!

## 📦 Step 1: Install Prerequisites

### Python
- Download Python 3.8+ from [python.org](https://www.python.org/downloads/)
- Verify installation: `python --version`

### Node.js
- Download Node.js 16+ from [nodejs.org](https://nodejs.org/)
- Verify installation: `node --version` and `npm --version`

## 🚀 Step 2: Quick Start

### Option A: Automated Setup (Recommended)

**Windows:**
```bash
run.bat
```

**Mac/Linux:**
```bash
chmod +x run.sh
./run.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Start both backend and frontend servers

### Option B: Manual Setup

**Backend:**
```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create data directory
mkdir data\catalog  # Windows
mkdir -p data/catalog  # Mac/Linux

# Start server
uvicorn backend.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

## 📸 Step 3: Add Product Images

1. Place product images in `data/catalog/` directory
2. Supported formats: JPG, PNG, BMP, GIF
3. Name files descriptively (e.g., `red_sneakers_nike.jpg`)

**Example Structure:**
```
data/
└── catalog/
    ├── laptop_dell_xps.jpg
    ├── phone_iphone_13.jpg
    ├── headphones_sony.jpg
    ├── watch_apple.jpg
    └── ... more products
```

### Download Sample Images

You can use any product images from:
- Your own products
- Stock photo websites (check licenses)
- Public datasets like:
  - [Stanford Products Dataset](https://cvgl.stanford.edu/projects/lifted_struct/)
  - [DeepFashion](http://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html)

## 🎨 Step 4: Access the Application

Once both servers are running:

1. **Frontend UI**: http://localhost:3000
2. **API Documentation**: http://localhost:8000/docs
3. **API Base URL**: http://localhost:8000

## 🧪 Step 5: Test the System

1. Go to http://localhost:3000
2. Drag and drop a product image or click to upload
3. Wait for the search results
4. View similar products ranked by similarity!

## 🔧 Troubleshooting

### Backend Issues

**"Module not found" error:**
```bash
pip install -r requirements.txt --upgrade
```

**TensorFlow installation issues:**
```bash
# For CPU-only version (lighter)
pip install tensorflow-cpu==2.15.0
```

**Port already in use:**
```bash
# Use different port
uvicorn backend.main:app --port 8001
```

### Frontend Issues

**"Cannot find module" error:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Port 3000 in use:**
```bash
# React will prompt to use different port
# Or set PORT environment variable
PORT=3001 npm start
```

### API Connection Issues

If frontend can't connect to backend:

1. Create `frontend/.env` file:
```
REACT_APP_API_URL=http://localhost:8000
```

2. Restart frontend server

## 📊 Performance Tips

### For Faster Searches:
1. Use GPU version of TensorFlow if you have NVIDIA GPU
2. Pre-build the index with all catalog images
3. Use FAISS GPU version for large catalogs (10K+ images)

### For Better Results:
1. Use high-quality product images
2. Consistent image backgrounds
3. Similar lighting conditions
4. Focus on the product (minimal background)

## 🚀 Next Steps

### Add More Products
```bash
# Via API
curl -X POST "http://localhost:8000/add-product" \
  -F "file=@product.jpg" \
  -F "product_id=prod_123" \
  -F "name=Product Name" \
  -F "category=Electronics" \
  -F "price=99.99"
```

### Customize the Model
Edit `backend/feature_extractor.py` to use different models:
- VGG16 (smaller, faster)
- InceptionV3 (balanced)
- EfficientNet (state-of-the-art)

### Deploy to Production
See README.md deployment section for production setup

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [TensorFlow Keras Applications](https://www.tensorflow.org/api_docs/python/tf/keras/applications)
- [FAISS Documentation](https://github.com/facebookresearch/faiss/wiki)
- [React Documentation](https://react.dev/)

## 💡 Tips for Best Results

1. **Image Quality**: Use clear, well-lit product photos
2. **Catalog Size**: Start with 10-50 products to test
3. **Similar Products**: Ensure catalog has visually similar items
4. **Consistent Format**: Same image dimensions and formats work best
5. **Regular Updates**: Add new products via the API endpoint

---

**Need Help?** Check the README.md or open an issue!

Happy searching! 🔍✨