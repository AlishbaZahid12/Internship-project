"""
Abstract contracts for swappable components (CV models, OCR engines,
embedding models). Concrete implementations (Phase 2/3) inherit from
these. Every other layer of the app depends on these interfaces, NOT
on any specific library — so you can swap YOLO for something else, or
EasyOCR for Tesseract, without touching the service layer or UI.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ObjectDetector(ABC):
    """Contract for any object detection backend used in scene description."""

    @abstractmethod
    def detect(self, frame) -> List[Dict[str, Any]]:
        """
        Returns a list of detections, each like:
        {"label": "chair", "position": "left", "confidence": 0.87}
        """
        raise NotImplementedError


class OCREngine(ABC):
    """Contract for any OCR backend used in product/medicine scanning."""

    @abstractmethod
    def extract_text(self, frame) -> str:
        """Returns all readable text found in the frame."""
        raise NotImplementedError


class EmbeddingModel(ABC):
    """Contract for any text embedding backend used in the RAG engine."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Returns a vector embedding for the given text."""
        raise NotImplementedError

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Returns embeddings for a batch of texts (more efficient)."""
        raise NotImplementedError


class SpeechToTextEngine(ABC):
    @abstractmethod
    def listen(self) -> str:
        raise NotImplementedError


class TextToSpeechEngine(ABC):
    @abstractmethod
    def speak(self, text: str, lang: str = "en") -> None:
        raise NotImplementedError
    
class NotificationSender(ABC):
    @abstractmethod
    def send(self, phone_number: str, message: str) -> tuple:
        """Returns (success: bool, detail: str)."""
        raise NotImplementedError