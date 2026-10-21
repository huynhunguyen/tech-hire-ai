"""Append-only, hash-chained audit trail (Art. 12 record keeping).

Each record stores the hash of its predecessor and a SHA-256 hash over its own canonical content.
Editing, reordering or deleting any record in the middle of the file breaks the chain, so tampering
becomes detectable. Truncating the tail is not detectable from the file alone; production systems
should additionally anchor the latest hash in WORM storage or an external timestamping service.
"""

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from pathlib import Path

from techhire.domain.exceptions import AuditLogCorruptedError
from techhire.domain.models import AuditRecord, DecisionRequest

GENESIS_HASH = "0" * 64
AUDIT_WRITE_LOCK = threading.Lock()


@dataclass(frozen=True)
class IntegrityReport:
    is_valid: bool
    record_count: int
    broken_at_line: int | None
    message: str


def compute_record_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hashed_payload(record_data: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in record_data.items() if key != "record_hash"}


class AuditLogger:
    def __init__(self, log_path: Path):
        self.log_path_ = Path(log_path)

    @property
    def log_path(self) -> Path:
        return self.log_path_

    def append(self, request: DecisionRequest) -> AuditRecord:
        with AUDIT_WRITE_LOCK:
            records = self.read_records()
            previous_hash = records[-1].record_hash if records else GENESIS_HASH
            payload = {
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "hr_id": request.hr_id,
                "candidate_id": request.candidate_id,
                "ai_score": round(request.ai_score, 4),
                "ai_recommendation": request.ai_recommendation.value,
                "hr_decision": request.hr_decision.value,
                "is_override": request.is_override,
                "justification": request.justification.strip(),
                "model_version": request.model_version,
                "previous_hash": previous_hash,
            }
            record = AuditRecord(**payload, record_hash=compute_record_hash(payload))

            self.log_path_.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path_.open("a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                log_file.flush()
            return record

    def read_records(self) -> list[AuditRecord]:
        return [AuditRecord(**data) for _, data in self._read_lines()]

    def recent_justifications(self, hr_id: str, limit: int) -> list[str]:
        own_records = [record for record in self.read_records() if record.hr_id == hr_id]
        return [record.justification for record in own_records[-limit:]]

    def verify_integrity(self) -> IntegrityReport:
        try:
            lines = self._read_lines()
        except AuditLogCorruptedError as error:
            return IntegrityReport(False, 0, None, str(error))

        expected_previous = GENESIS_HASH
        for index, (line_number, data) in enumerate(lines):
            if data.get("previous_hash") != expected_previous:
                return IntegrityReport(
                    False, index, line_number, f"Dòng {line_number}: liên kết chuỗi băm bị đứt (bản ghi bị xóa/chèn)."
                )
            if compute_record_hash(_hashed_payload(data)) != data.get("record_hash"):
                return IntegrityReport(
                    False, index, line_number, f"Dòng {line_number}: nội dung bản ghi đã bị sửa đổi sau khi ghi."
                )
            expected_previous = data["record_hash"]
        return IntegrityReport(True, len(lines), None, f"Toàn vẹn: {len(lines)} bản ghi, chuỗi băm hợp lệ.")

    def _read_lines(self) -> list[tuple[int, dict[str, object]]]:
        if not self.log_path_.exists():
            return []
        expected_keys = {field.name for field in fields(AuditRecord)}
        parsed = []
        with self.log_path_.open("r", encoding="utf-8") as log_file:
            for line_number, line in enumerate(log_file, start=1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as error:
                    raise AuditLogCorruptedError(f"Dòng {line_number}: không phải JSON hợp lệ ({error.msg}).") from error
                if set(data) != expected_keys:
                    raise AuditLogCorruptedError(f"Dòng {line_number}: cấu trúc bản ghi không đúng lược đồ.")
                parsed.append((line_number, data))
        return parsed
