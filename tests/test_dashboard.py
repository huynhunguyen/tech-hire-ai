"""Headless smoke test of the Streamlit dashboard using Streamlit's AppTest harness."""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def dashboard(tmp_path, monkeypatch) -> AppTest:
    monkeypatch.setenv("TECHHIRE_AUDIT_LOG_PATH", str(tmp_path / "audit_log.jsonl"))
    monkeypatch.delenv("TECHHIRE_DATASET_PATH", raising=False)
    # The composed system is cached process-wide; clear it so each test gets its own audit log path.
    st.cache_resource.clear()
    app = AppTest.from_file(str(APP_PATH), default_timeout=120)
    app.run()
    return app


def test_dashboard_renders_all_three_areas(dashboard):
    assert not dashboard.exception
    assert len(dashboard.tabs) == 3


def test_hr_decision_flow_writes_audit_record(dashboard, tmp_path):
    dashboard.text_input(key="oversight_hr_id").input("HR-002")
    dashboard.radio(key="oversight_decision").set_value("Mời phỏng vấn")
    dashboard.text_area(key="oversight_justification").input(
        "Kỹ năng lập trình và kết quả phỏng vấn chuyên môn đáp ứng tốt yêu cầu vị trí."
    )
    dashboard.checkbox(key="oversight_attestation").check()
    dashboard.run()
    next(button for button in dashboard.button if button.label == "Xác nhận quyết định").click()
    dashboard.run()

    assert not dashboard.exception
    assert any("Đã ghi nhận quyết định" in message.value for message in dashboard.success)
    log_lines = (tmp_path / "audit_log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 1
