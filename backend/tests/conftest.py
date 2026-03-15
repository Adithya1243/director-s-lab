"""
Shared fixtures for Director's Lab backend tests.

All GCP clients (Gemini, Imagen, Firestore, GCS) are replaced with mocks so
tests never touch external services.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport

import agent
from main import app


@pytest_asyncio.fixture
async def async_client():
    """
    FastAPI test client with lifespan active but GCP initialization mocked.

    `agent.initialize_clients()` is replaced with a no-op so startup never
    tries to reach Gemini, Vertex AI, Firestore, or Cloud Storage.
    Module-level client globals are set to MagicMock so any stray direct
    reference doesn't raise AttributeError on None.
    """
    with patch("agent.initialize_clients"), \
         patch.object(agent, "gemini_client", MagicMock()), \
         patch.object(agent, "gcs_client",    MagicMock()), \
         patch.object(agent, "firestore_client", MagicMock()):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client


# ---------------------------------------------------------------------------
# Shared sample data used across multiple test modules
# ---------------------------------------------------------------------------

SAMPLE_SCENE = {
    "scene_id":            "test-scene-abc-123",
    "scene_prompt":        "A detective finds a letter from her dead sister — written yesterday.",
    "clarifying_question": "What's the emotional core — grief or dread?",
    "clarification":       "Both. She can't tell if it's a miracle or a threat.",
    "scene_summary":       "A haunting discovery unravels a detective's certainty.",
    "beat_map":            {"tension": 70, "longing": 60, "resolve": 20},
    "panels": [
        {
            "panel_number":       1,
            "visual_description": "Detective at cluttered desk, envelope in hand.",
            "dialogue":           "It can't be.",
            "direction_note":     "Stunned — hand trembling slightly.",
            "camera_angle":       "Close-up, rack focus from envelope to face.",
            "image_prompt":       "Detective stunned, close-up, film noir lighting.",
            "image_url":          "https://storage.googleapis.com/bucket/panels/test-scene-abc-123/panel_1.png",
        },
        {
            "panel_number":       2,
            "visual_description": "Letter unfolds — her sister's handwriting.",
            "dialogue":           "[SILENCE]",
            "direction_note":     "Trembling — barely breathing.",
            "camera_angle":       "Extreme close-up, shallow depth of field.",
            "image_prompt":       "Handwritten letter, extreme close-up, warm candlelight.",
            "image_url":          "https://storage.googleapis.com/bucket/panels/test-scene-abc-123/panel_2.png",
        },
        {
            "panel_number":       3,
            "visual_description": "Rain streaks the window. City blurs behind her.",
            "dialogue":           "She knew.",
            "direction_note":     "Hollow delivery — a statement, not a question.",
            "camera_angle":       "Wide shot, detective silhouetted against rain.",
            "image_prompt":       "Silhouette by rainy window, wide shot, desaturated.",
            "image_url":          "https://storage.googleapis.com/bucket/panels/test-scene-abc-123/panel_3.png",
        },
        {
            "panel_number":       4,
            "visual_description": "She pockets the letter and stands.",
            "dialogue":           "[SILENCE]",
            "direction_note":     "Determined — grief becomes purpose.",
            "camera_angle":       "Low-angle dolly push as she rises.",
            "image_prompt":       "Detective rising, low angle, dramatic shadow.",
            "image_url":          "https://storage.googleapis.com/bucket/panels/test-scene-abc-123/panel_4.png",
        },
    ],
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}
