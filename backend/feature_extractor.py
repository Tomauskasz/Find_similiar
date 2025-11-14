import tensorflow as tf
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.preprocessing import image
import numpy as np
from PIL import Image

class FeatureExtractor:
    def __init__(self, model_name='resnet50'):
        """
        Initialize feature extractor with pre-trained model
        """
        self.model_name = model_name
        self.target_size = (224, 224)
        
        # Load pre-trained ResNet50 without top classification layer
        self.model = ResNet50(
            weights='imagenet',
            include_top=False,
            pooling='avg',  # Global average pooling
            input_shape=(224, 224, 3)
        )
        
        self.feature_dim = 2048  # ResNet50 output dimension
        
        print(f"Loaded {model_name} model for feature extraction")
    
    def preprocess_image(self, img: Image.Image) -> np.ndarray:
        """
        Preprocess PIL Image for model input
        """
        # Resize image
        img = img.resize(self.target_size)
        
        # Convert to array
        img_array = image.img_to_array(img)
        
        # Add batch dimension
        img_array = np.expand_dims(img_array, axis=0)
        
        # Preprocess for ResNet50
        img_array = preprocess_input(img_array)
        
        return img_array
    
    def extract_features(self, img: Image.Image) -> np.ndarray:
        """
        Extract feature vector from image
        """
        # Preprocess
        processed_img = self.preprocess_image(img)
        
        # Extract features
        features = self.model.predict(processed_img, verbose=0)
        
        # Normalize features for cosine similarity
        features = features / np.linalg.norm(features)
        
        return features.flatten()
    
    def extract_features_batch(self, images: list) -> np.ndarray:
        """
        Extract features from multiple images
        """
        processed_images = [self.preprocess_image(img) for img in images]
        batch = np.vstack(processed_images)
        
        features = self.model.predict(batch, verbose=0)
        
        # Normalize each feature vector
        features = features / np.linalg.norm(features, axis=1, keepdims=True)
        
        return features