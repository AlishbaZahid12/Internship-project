"""
Business logic for logging scans. The actual risk-checking logic
(RAG + embeddings) plugs in here in Phase 3.
"""

from database.repositories.scan_repository import ScanRepository


class ScanService:

    def __init__(self, scan_repo: ScanRepository = None):
        self.scan_repo = scan_repo or ScanRepository()

    def record_scan(self, user_id: int, item_name: str, extracted_text: str,
                     verdict: str, reason: str):
        self.scan_repo.log(user_id, item_name, extracted_text, verdict, reason)

    def get_history(self, user_id: int, limit: int = 20):
        return self.scan_repo.find_by_user_id(user_id, limit)