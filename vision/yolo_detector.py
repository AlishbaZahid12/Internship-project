"""
Concrete YOLO implementation of the ObjectDetector interface.
If you ever swap detection libraries later, only this file changes —
nothing else in the app needs to know YOLO exists.
"""

from ultralytics import YOLO
from core.interfaces import ObjectDetector
from core.exceptions import ModelLoadError
from core.logger import get_logger
from config import MODEL_CONFIG

logger = get_logger(__name__)


class YoloObjectDetector(ObjectDetector):

    def __init__(self):
        try:
            self.model = YOLO(MODEL_CONFIG.yolo_model_path)
            logger.info("YOLO model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise ModelLoadError(str(e))

    def detect(self, frame) -> list:
        """
        Returns: [{"label": "chair", "position": "left", "confidence": 0.87}, ...]
        """
        results = self.model(frame, verbose=False)[0]
        frame_width = frame.shape[1]
        detections = []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            label = self.model.names[cls_id]
            confidence = float(box.conf[0])

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            box_center_x = (x1 + x2) / 2

            if box_center_x < frame_width / 3:
                position = "left"
            elif box_center_x < (2 * frame_width) / 3:
                position = "center"
            else:
                position = "right"

            detections.append({
                "label": label,
                "position": position,
                "confidence": round(confidence, 2)
            })

        return detections