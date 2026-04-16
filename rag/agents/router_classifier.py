"""
Query Intent Classifier for Agentic RAG system.

Uses lightweight ML (logistic regression) for query classification:
- Handles queries that don't match rule-based keywords
- Provides confidence scores for routing decisions
- Can be trained on historical query data
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from rag.core.config import get_config

logger = logging.getLogger(__name__)


class QueryIntentClassifier:
    """
    Lightweight ML-based query intent classifier.

    Features:
    - TF-IDF feature extraction
    - Logistic regression classification
    - Confidence score output
    - Fallback to rule-based classification when model not trained
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the query intent classifier.

        Args:
            config: Optional configuration override
        """
        self.config = config or get_config().get('router', {})
        self._model = None
        self._vectorizer = None
        self._is_trained = False

    def _ensure_model(self) -> bool:
        """
        Ensure ML model is available.

        Returns:
            True if model is ready, False if fallback mode
        """
        if self._model is not None and self._is_trained:
            return True

        # Try to load a pre-trained model
        # For now, return False to indicate fallback mode
        # In production, this would load from a file
        logger.debug('ML classifier not trained, using fallback mode')
        return False

    def train(self, queries: List[str], labels: List[str]) -> bool:
        """
        Train the classifier on labeled queries.

        Args:
            queries: List of query texts
            labels: List of labels ('agentic' or 'simple')

        Returns:
            True if training succeeded, False otherwise
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression

            # Extract TF-IDF features
            self._vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                stop_words=None  # Chinese doesn't have standard stop words
            )
            X = self._vectorizer.fit_transform(queries)

            # Train logistic regression
            self._model = LogisticRegression(
                max_iter=1000,
                class_weight='balanced',
                random_state=42
            )
            self._model.fit(X, labels)
            self._is_trained = True

            logger.info(f'Trained classifier on {len(queries)} samples')
            return True

        except ImportError:
            logger.warning('sklearn not available, using fallback mode')
            return False
        except Exception as e:
            logger.error(f'Failed to train classifier: {e}')
            return False

    def classify(self, query: str) -> Tuple[str, float]:
        """
        Classify a query's intent.

        Args:
            query: User query text

        Returns:
            Tuple of (label, confidence_score)
            Label is 'agentic' or 'simple'
            Confidence is 0.0-1.0
        """
        # Try ML classification
        if self._ensure_model():
            try:
                X = self._vectorizer.transform([query])
                prediction = self._model.predict(X)[0]
                probabilities = self._model.predict_proba(X)[0]
                confidence = float(max(probabilities))

                logger.debug(f'ML classification: {prediction} (confidence: {confidence:.2f})')
                return prediction, confidence

            except Exception as e:
                logger.warning(f'ML classification failed: {e}')

        # Fallback: return uncertain classification
        # The router should use rule-based classification as primary
        logger.debug('Using fallback classification')
        return 'simple', 0.5  # Neutral confidence

    def batch_classify(self, queries: List[str]) -> List[Tuple[str, float]]:
        """
        Classify multiple queries in batch.

        Args:
            queries: List of query texts

        Returns:
            List of (label, confidence) tuples
        """
        if not self._ensure_model():
            # Fallback mode
            return [('simple', 0.5) for _ in queries]

        try:
            X = self._vectorizer.transform(queries)
            predictions = self._model.predict(X)
            probabilities = self._model.predict_proba(X)

            results = []
            for pred, probs in zip(predictions, probabilities):
                confidence = float(max(probs))
                results.append((pred, confidence))

            return results

        except Exception as e:
            logger.error(f'Batch classification failed: {e}')
            return [('simple', 0.5) for _ in queries]

    def save_model(self, path: str) -> bool:
        """
        Save trained model to disk.

        Args:
            path: Directory path to save model files

        Returns:
            True if save succeeded, False otherwise
        """
        if not self._is_trained:
            logger.warning('Cannot save untrained model')
            return False

        try:
            import pickle
            import os

            os.makedirs(path, exist_ok=True)

            with open(os.path.join(path, 'classifier.pkl'), 'wb') as f:
                pickle.dump(self._model, f)

            with open(os.path.join(path, 'vectorizer.pkl'), 'wb') as f:
                pickle.dump(self._vectorizer, f)

            logger.info(f'Saved model to {path}')
            return True

        except Exception as e:
            logger.error(f'Failed to save model: {e}')
            return False

    def load_model(self, path: str) -> bool:
        """
        Load trained model from disk.

        Args:
            path: Directory path containing model files

        Returns:
            True if load succeeded, False otherwise
        """
        try:
            import pickle
            import os

            model_path = os.path.join(path, 'classifier.pkl')
            vectorizer_path = os.path.join(path, 'vectorizer.pkl')

            if not os.path.exists(model_path) or not os.path.exists(vectorizer_path):
                logger.warning(f'Model files not found in {path}')
                return False

            with open(model_path, 'rb') as f:
                self._model = pickle.load(f)

            with open(vectorizer_path, 'rb') as f:
                self._vectorizer = pickle.load(f)

            self._is_trained = True
            logger.info(f'Loaded model from {path}')
            return True

        except Exception as e:
            logger.error(f'Failed to load model: {e}')
            return False


# Global instance
intent_classifier = QueryIntentClassifier()
