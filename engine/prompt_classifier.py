import os
import pickle
import logging
from typing import Dict, Any
from engine.dataset_generator import DatasetGenerator

logger = logging.getLogger("secureprompt")

class PromptClassifier:
    def __init__(self, model_dir: str = "model"):
        self.model_dir = model_dir
        self.vectorizer_path = os.path.join(model_dir, "classifier_9class_vec.pkl")
        self.classifier_path = os.path.join(model_dir, "classifier_9class_cls.pkl")
        
        self.vectorizer = None
        self.classifier = None
        
        # 9 Required Categories list
        self.categories = [
            "General", "Programming", "Finance", "Healthcare", 
            "HR", "Legal", "Customer Data", "Internal Document", "Security"
        ]

        self._init_model()

    def _init_model(self):
        """
        Initializes vectorizers and classifiers from disk.
        If files do not exist, automatically generates a training set and trains the model.
        """
        os.makedirs(self.model_dir, exist_ok=True)

        if os.path.exists(self.vectorizer_path) and os.path.exists(self.classifier_path):
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    with open(self.vectorizer_path, "rb") as f:
                        self.vectorizer = pickle.load(f)
                    with open(self.classifier_path, "rb") as f:
                        self.classifier = pickle.load(f)
                logger.info("Loaded 9-class Prompt Classifier.")
            except Exception as e:
                logger.error(f"Failed to load 9-class prompt classifier: {e}. Re-training model.")
                self.train_and_save()
        else:
            logger.info("9-class prompt classifier files not found. Automatically training...")
            self.train_and_save()

    def train_and_save(self):
        """
        Generates 9-class dataset, fits a Logistic Regression model, and saves it.
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            
            # Generate dataset (35 samples per class)
            df = DatasetGenerator.generate_multiclass_dataframe(size_per_class=35)
            X = df["text"]
            y = df["category"]

            # Vectorize
            self.vectorizer = TfidfVectorizer(max_features=1200, ngram_range=(1, 2))
            X_vec = self.vectorizer.fit_transform(X)

            # Fit Classifier
            self.classifier = LogisticRegression(C=2.0, max_iter=300)
            self.classifier.fit(X_vec, y)

            # Save models
            with open(self.vectorizer_path, "wb") as f:
                pickle.dump(self.vectorizer, f)
            with open(self.classifier_path, "wb") as f:
                pickle.dump(self.classifier, f)
            
            logger.info("9-class prompt classifier trained and saved successfully.")
        except Exception as e:
            logger.error(f"Failed to train 9-class prompt classifier: {e}")

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predicts category, confidence score, and associated risk level for a prompt.
        """
        if not text.strip():
            return {
                "category": "General",
                "confidence": 0,
                "risk_level": "LOW"
            }

        if not self.vectorizer or not self.classifier:
            return {
                "category": "General",
                "confidence": 50,
                "risk_level": "LOW"
            }

        try:
            vec = self.vectorizer.transform([text])
            probabilities = self.classifier.predict_proba(vec)[0]
            
            # Find best class
            best_idx = probabilities.argmax()
            predicted_class = self.classifier.classes_[best_idx]
            confidence = int(probabilities[best_idx] * 100)

            # Risk Level Mapping:
            # - Security -> CRITICAL
            # - Healthcare, Customer Data, Legal -> HIGH
            # - Finance, Internal Document, HR -> MEDIUM
            # - Programming, General -> LOW
            risk_mapping = {
                "Security": "CRITICAL",
                "Healthcare": "HIGH",
                "Customer Data": "HIGH",
                "Legal": "HIGH",
                "Finance": "MEDIUM",
                "Internal Document": "MEDIUM",
                "HR": "MEDIUM",
                "Programming": "LOW",
                "General": "LOW"
            }
            
            risk_level = risk_mapping.get(predicted_class, "LOW")

            return {
                "category": predicted_class,
                "confidence": confidence,
                "risk_level": risk_level
            }
        except Exception as e:
            logger.error(f"Inference error in 9-class classifier: {e}")
            
        return {
            "category": "General",
            "confidence": 0,
            "risk_level": "LOW"
        }
