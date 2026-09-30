
from core.interfaces import ObjectDetector, OCREngine
from core.logger import get_logger

logger = get_logger(__name__)


class VisionService:

    def __init__(self, detector: ObjectDetector, ocr_engine: OCREngine):
        self.detector = detector
        self.ocr_engine = ocr_engine

    def describe_scene(self, frame) -> str:
        detections = self.detector.detect(frame)
        return self._build_scene_sentence(detections)

    def scan_product_label(self, frame) -> str:
        text = self.ocr_engine.extract_text(frame)
        logger.info(f"OCR extracted text: {text}")
        return text

    @staticmethod
    def _build_scene_sentence(detections: list) -> str:
        detections = [d for d in detections if d["confidence"] >= 0.6]
        if not detections:
            return "I don't see any recognizable objects clearly right now."

        phrases = []
        for d in detections:
            phrases.append(
                f"a {d['label']} in the center" if d["position"] == "center"
                else f"a {d['label']} on your {d['position']}"
            )

        if len(phrases) == 1:
            return f"There is {phrases[0]}."
        return "There is " + ", ".join(phrases[:-1]) + f", and {phrases[-1]}."