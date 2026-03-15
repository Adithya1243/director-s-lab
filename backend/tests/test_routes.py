"""
Route validation + error-code tests (FastAPI layer only).

Agent functions are mocked — these tests verify:
  • Correct HTTP status codes (200, 404, 422, 504)
  • Request payload validation (min_length, required fields)
  • Error propagation (ValueError → 404, TimeoutError → 504, Exception → 500)
  • Response shape matches declared Pydantic models
"""

import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import SAMPLE_SCENE


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

async def test_health_ok(async_client):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "directors-lab"


# ---------------------------------------------------------------------------
# POST /api/scene/clarify
# ---------------------------------------------------------------------------

async def test_clarify_success(async_client):
    with patch("agent.ask_clarifying_question", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = {
            "scene_id": "scene-abc-123",
            "question": "What's the emotional core — grief or dread?",
        }
        resp = await async_client.post(
            "/api/scene/clarify",
            json={"scene_prompt": "A detective finds a letter from her dead sister."},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["scene_id"] == "scene-abc-123"
    assert "question" in body
    assert len(body["question"]) > 0


async def test_clarify_empty_prompt_is_rejected(async_client):
    """min_length=1 — blank prompt must return 422 Unprocessable Entity."""
    resp = await async_client.post("/api/scene/clarify", json={"scene_prompt": ""})
    assert resp.status_code == 422


async def test_clarify_missing_field_is_rejected(async_client):
    resp = await async_client.post("/api/scene/clarify", json={})
    assert resp.status_code == 422


async def test_clarify_timeout_returns_504(async_client):
    with patch("agent.ask_clarifying_question", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = TimeoutError("Gemini timed out")
        resp = await async_client.post(
            "/api/scene/clarify",
            json={"scene_prompt": "A detective walks in"},
        )
    assert resp.status_code == 504


async def test_clarify_unexpected_error_returns_500(async_client):
    with patch("agent.ask_clarifying_question", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = RuntimeError("unexpected")
        resp = await async_client.post(
            "/api/scene/clarify",
            json={"scene_prompt": "A detective walks in"},
        )
    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/scene/generate
# ---------------------------------------------------------------------------

async def test_generate_success(async_client):
    with patch("agent.generate_scene", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = SAMPLE_SCENE
        resp = await async_client.post(
            "/api/scene/generate",
            json={
                "scene_id":            SAMPLE_SCENE["scene_id"],
                "scene_prompt":        SAMPLE_SCENE["scene_prompt"],
                "clarifying_question": SAMPLE_SCENE["clarifying_question"],
                "clarification":       SAMPLE_SCENE["clarification"],
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["scene_id"]   == SAMPLE_SCENE["scene_id"]
    assert len(body["panels"]) == 4


async def test_generate_missing_fields_rejected(async_client):
    """All four fields are required — missing any returns 422."""
    resp = await async_client.post(
        "/api/scene/generate",
        json={"scene_id": "abc"},
    )
    assert resp.status_code == 422


async def test_generate_empty_clarification_rejected(async_client):
    resp = await async_client.post(
        "/api/scene/generate",
        json={
            "scene_id":            "abc",
            "scene_prompt":        "A scene",
            "clarifying_question": "What mood?",
            "clarification":       "",  # empty — min_length=1
        },
    )
    assert resp.status_code == 422


async def test_generate_timeout_returns_504(async_client):
    with patch("agent.generate_scene", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = TimeoutError()
        resp = await async_client.post(
            "/api/scene/generate",
            json={
                "scene_id":            "abc",
                "scene_prompt":        "A scene",
                "clarifying_question": "What mood?",
                "clarification":       "Grief",
            },
        )
    assert resp.status_code == 504


# ---------------------------------------------------------------------------
# POST /api/scene/{scene_id}/preview-revision
# ---------------------------------------------------------------------------

async def test_preview_revision_success(async_client):
    proposal = {
        "scene_id":           SAMPLE_SCENE["scene_id"],
        "revision_note":      "make it darker",
        "current_beat_map":   SAMPLE_SCENE["beat_map"],
        "proposed_beat_map":  {"tension": 90, "longing": 55, "resolve": 10},
        "beat_map_rationale": "Darker tone amplifies dread.",
        "proposed_panels": [
            {
                "panel_number":   1,
                "change_type":    "revise",
                "reason":         "Heavier atmosphere.",
                "change_summary": "Add shadows.",
            }
        ],
    }
    with patch("agent.preview_revision", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = proposal
        resp = await async_client.post(
            f"/api/scene/{SAMPLE_SCENE['scene_id']}/preview-revision",
            json={"revision_note": "make it darker"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["scene_id"]          == SAMPLE_SCENE["scene_id"]
    assert "proposed_beat_map" in body
    assert "proposed_panels"   in body


async def test_preview_revision_empty_note_rejected(async_client):
    resp = await async_client.post(
        "/api/scene/abc/preview-revision",
        json={"revision_note": ""},
    )
    assert resp.status_code == 422


async def test_preview_revision_scene_not_found_returns_404(async_client):
    with patch("agent.preview_revision", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = ValueError("Scene xyz not found")
        resp = await async_client.post(
            "/api/scene/xyz/preview-revision",
            json={"revision_note": "darker"},
        )
    assert resp.status_code == 404


async def test_preview_revision_timeout_returns_504(async_client):
    with patch("agent.preview_revision", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = TimeoutError()
        resp = await async_client.post(
            "/api/scene/abc/preview-revision",
            json={"revision_note": "darker"},
        )
    assert resp.status_code == 504


# ---------------------------------------------------------------------------
# POST /api/scene/{scene_id}/revise
# ---------------------------------------------------------------------------

async def test_revise_success(async_client):
    with patch("agent.revise_scene", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = {
            **SAMPLE_SCENE,
            "affected_panels": [2],
        }
        resp = await async_client.post(
            f"/api/scene/{SAMPLE_SCENE['scene_id']}/revise",
            json={"revision_note": "make it darker", "approved_panels": [2]},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["scene_id"] == SAMPLE_SCENE["scene_id"]
    assert len(body["panels"]) == 4


async def test_revise_empty_approved_panels_rejected(async_client):
    """min_length=1 on approved_panels — empty list must return 422."""
    resp = await async_client.post(
        "/api/scene/abc/revise",
        json={"revision_note": "darker", "approved_panels": []},
    )
    assert resp.status_code == 422


async def test_revise_missing_approved_panels_rejected(async_client):
    resp = await async_client.post(
        "/api/scene/abc/revise",
        json={"revision_note": "darker"},
    )
    assert resp.status_code == 422


async def test_revise_empty_revision_note_rejected(async_client):
    resp = await async_client.post(
        "/api/scene/abc/revise",
        json={"revision_note": "", "approved_panels": [1]},
    )
    assert resp.status_code == 422


async def test_revise_scene_not_found_returns_404(async_client):
    with patch("agent.revise_scene", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = ValueError("Scene abc not found")
        resp = await async_client.post(
            "/api/scene/abc/revise",
            json={"revision_note": "darker", "approved_panels": [1]},
        )
    assert resp.status_code == 404


async def test_revise_timeout_returns_504(async_client):
    with patch("agent.revise_scene", new_callable=AsyncMock) as mock_fn:
        mock_fn.side_effect = TimeoutError()
        resp = await async_client.post(
            "/api/scene/abc/revise",
            json={"revision_note": "darker", "approved_panels": [1]},
        )
    assert resp.status_code == 504


# ---------------------------------------------------------------------------
# GET /api/scene/{scene_id}
# ---------------------------------------------------------------------------

async def test_get_scene_success(async_client):
    with patch("agent.get_scene", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = SAMPLE_SCENE
        resp = await async_client.get(f"/api/scene/{SAMPLE_SCENE['scene_id']}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["scene_id"] == SAMPLE_SCENE["scene_id"]
    assert len(body["panels"]) == 4


async def test_get_scene_not_found_returns_404(async_client):
    with patch("agent.get_scene", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = None
        resp = await async_client.get("/api/scene/nonexistent-id")

    assert resp.status_code == 404
