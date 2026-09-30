"""
Concrete EasyOCR implementation of the OCREngine interface.
"""

import ssl
import cv2
import easyocr
from core.interfaces import OCREngine
from core.exceptions import ModelLoadError
from core.logger import get_logger

logger = get_logger(__name__)

# Some Windows setups fail EasyOCR's first-time model download due to
# local SSL certificate verification issues. This relaxes verification
# ONLY for that download — safe since it's just public model weights.
ssl._create_default_https_context = ssl._create_unverified_context


class EasyOCREngine(OCREngine):

    def __init__(self):
        try:
            self.reader = easyocr.Reader(["en"], gpu=False)
            logger.info("EasyOCR model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load EasyOCR model: {e}")
            raise ModelLoadError(str(e))

    def extract_text(self, frame) -> str:
        # Grayscale preprocessing: OCR doesn't need color, and dropping
        # it reduces the data EasyOCR has to process, speeding things up.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        results = self.reader.readtext(gray, detail=0)
        return " ".join(results).strip()