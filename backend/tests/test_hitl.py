"""
HITL (Human-in-the-Loop) Revision Loop — Contract Tests.

These tests verify the core guarantee of the revision system:
  1. preview_revision NEVER calls Imagen (no images generated until human approves)
  2. revise_scene ONLY generates images for human-approved panels
  3. Unapproved panels keep their original content AND original image URLs
  4. The safety guard in revise_scene filters extra panels even if Gemini returns them
  5. Image generation failures produce a placeholder URL — scene still saves

All external I/O (Gemini, Imagen, Firestore, GCS) is mocked.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, call

import agent
from tests.conftest import SAMPLE_SCENE


# ---------------------------------------------------------------------------
# Shared mock responses
# ---------------------------------------------------------------------------

PREVIEW_RESPONSE = {
    "proposed_beat_map":  {"tension": 90, "longing": 55, "resolve": 10},
    "beat_map_rationale": "Darker tone amplifies dread over resolution.",
    "proposed_panels": [
        {
            "panel_number":   1,
            "change_type":    "revise",
            "reason":         "Open with heavier atmosphere.",
            "change_summary": "Add shadows and ominous lighting to the desk scene.",
        },
        {
            "panel_number":   3,
            "change_type":    "add_element",
            "reason":         "Reinforce isolation.",
            "change_summary": "Add a figure glimpsed through the rain-streaked window.",
        },
    ],
}

REVISION_PANEL_2_ONLY = {
    "beat_map": {"tension": 85, "longing": 60, "resolve": 10},
    "revised_panels": [
        {
            "panel_number":       2,
            "visual_description": "Letter in a black-gloved hand — ink still wet.",
            "dialogue":           "[SILENCE]",
            "direction_note":     "Trembling with dread.",
            "camera_angle":       "Extreme close-up, low-key lighting.",
            "image_prompt":       "Dark letter in gloved hand, extreme close-up.",
        },
    ],
}

REVISION_PANELS_1_AND_3 = {
    "beat_map": {"tension": 90, "longing": 55, "resolve": 10},
    "revised_panels": [
        {
            "panel_number":       1,
            "visual_description": "Detective at desk; shadows engulf the edges.",
            "dialogue":           "It can't be.",
            "direction_note":     "Stunned — world collapsing inward.",
            "camera_angle":       "Close-up, extreme low-key.",
            "image_prompt":       "Detective stunned in deep shadow, extreme low-key.",
        },
        {
            "panel_number":       3,
            "visual_description": "Rain window — a silhouette outside.",
            "dialogue":           "She knew.",
            "direction_note":     "Hollow, barely audible.",
            "camera_angle":       "Wide shot, figure visible through rain.",
            "image_prompt":       "Silhouette in rain through window, noir.",
        },
    ],
}


# ---------------------------------------------------------------------------
# Contract 1 — preview_revision never calls Imagen
# ---------------------------------------------------------------------------

async def test_preview_revision_never_calls_imagen():
    """
    The HITL preview step must NEVER invoke Imagen regardless of the directive.
    Violating this would charge image generation before human approval.
    """
    with patch.object(agent, "_load_scene",       new_callable=AsyncMock, return_value=SAMPLE_SCENE), \
         patch.object(agent, "_call_gemini_json",  new_callable=AsyncMock, return_value=json.dumps(PREVIEW_RESPONSE)), \
         patch.object(agent, "_generate_image",    new_callable=AsyncMock) as mock_imagen:

        result = await agent.preview_revision(SAMPLE_SCENE["scene_id"], "make it darker")

        mock_imagen.assert_not_called()
        assert "proposed_panels" in result
        assert len(result["proposed_panels"]) == 2


async def test_preview_revision_returns_correct_structure():
    with patch.object(agent, "_load_scene",      new_callable=AsyncMock, return_value=SAMPLE_SCENE), \
         patch.object(agent, "_call_gemini_json", new_callable=AsyncMock, return_value=json.dumps(PREVIEW_RESPONSE)), \
         patch.object(agent, "_generate_image",   new_callable=AsyncMock):

        result = await agent.preview_revision(SAMPLE_SCENE["scene_id"], "make it darker")

        assert result["scene_id"]            == SAMPLE_SCENE["scene_id"]
        assert result["revision_note"]       == "make it darker"
        assert result["current_beat_map"]    == SAMPLE_SCENE["beat_map"]
        assert result["proposed_beat_map"]   == PREVIEW_RESPONSE["proposed_beat_map"]
        assert result["beat_map_rationale"]  == PREVIEW_RESPONSE["beat_map_rationale"]


async def test_preview_revision_scene_not_found_raises():
    with patch.object(agent, "_load_scene", new_callable=AsyncMock, return_value=None):
        with pytest.raises(ValueError, match="not found"):
            await agent.preview_revision("nonexistent-id", "darker")


# ---------------------------------------------------------------------------
# Contract 2 — revise_scene calls Imagen only for approved panels
# ---------------------------------------------------------------------------

async def test_revise_only_calls_imagen_for_approved_panels():
    """
    Single approved panel [2] → Imagen called exactly once with panel_number=2.
    """
    with patch.object(agent, "_load_scene",      new_callable=AsyncMock, return_value=SAMPLE_SCENE), \
         patch.object(agent, "_call_gemini_json", new_callable=AsyncMock, return_value=json.dumps(REVISION_PANEL_2_ONLY)), \
         patch.object(agent, "_generate_image",   new_callable=AsyncMock, return_value="https://new/panel_2.png") as mock_imagen, \
         patch.object(agent, "_update_scene",     new_callable=AsyncMock):

        await agent.revise_scene(SAMPLE_SCENE["scene_id"], "make it darker", approved_panels=[2])

        assert mock_imagen.call_count == 1
        # Verify panel_num arg (3rd positional arg)
        _, _, panel_num = mock_imagen.call_args.args
        assert panel_num == 2


async def test_revise_multiple_approved_calls_imagen_for_each():
    """
    Two approved panels [1, 3] → Imagen called exactly twice.
    """
    with patch.object(agent, "_load_scene",      new_callable=AsyncMock, return_value=SAMPLE_SCENE), \
         patch.object(agent, "_call_gemini_json", new_callable=AsyncMock, return_value=json.dumps(REVISION_PANELS_1_AND_3)), \
         patch.object(agent, "_generate_image",   new_callable=AsyncMock, return_value="https://new/panel.png") as mock_imagen, \
         patch.object(agent, "_update_scene",     new_callable=AsyncMock):

        await agent.revise_scene(SAMPLE_SCENE["scene_id"], "darker", approved_panels=[1, 3])

        assert mock_imagen.call_count == 2
        called_panel_nums = {c.args[2] for c in mock_imagen.call_args_list}
        assert called_panel_nums == {1, 3}


# ---------------------------------------------------------------------------
# Contract 3 — unapproved panels keep original URL and content
# ---------------------------------------------------------------------------

async def test_unapproved_panels_keep_original_image_url():
    """
    Panels NOT in approved_panels must retain their original image_url unchanged.
    """
    new_url = "https://storage.new/panel_2_revised.png"

    with patch.object(agent, "_load_scene",      new_callable=AsyncMock, return_value=SAMPLE_SCENE), \
         patch.object(agent, "_call_gemini_json", new_callable=AsyncMock, return_value=json.dumps(REVISION_PANEL_2_ONLY)), \
         patch.object(agent, "_generate_image",   new_callable=AsyncMock, return_value=new_url), \
         patch.object(agent, "_update_scene",     new_callable=AsyncMock):

        result = await agent.revise_scene(SAMPLE_SCENE["scene_id"], "darker", approved_panels=[2])

    panels = {p["panel_number"]: p for p in result["panels"]}

    # Panel 2 → new URL
    assert panels[2]["image_url"] == new_url

    # Panels 1, 3, 4 → original URLs unchanged
    original = {p["panel_number"]: p for p in SAMPLE_SCENE["panels"]}
    assert panels[1]["image_url"] == original[1]["image_url"]
    assert panels[3]["image_url"] == original[3]["image_url"]
    assert panels[4]["image_url"] == original[4]["image_url"]


async def test_unapproved_panels_keep_original_content():
    """
    Panels NOT in approved_panels must also keep their original dialogue, visual_description, etc.
    """
    with patch.object(agent, "_load_scene",      new_callable=AsyncMock, return_value=SAMPLE_SCENE), \
         patch.object(agent, "_call_gemini_json", new_callable=AsyncMock, return_value=json.dumps(REVISION_PANEL_2_ONLY)), \
         patch.object(agent, "_generate_image",   new_callable=AsyncMock, return_value="https://new/url.png"), \
         patch.object(agent, "_update_scene",     new_callable=AsyncMock):

        result = await agent.revise_scene(SAMPLE_SCENE["scene_id"], "darker", approved_panels=[2])

    panels = {p["panel_number"]: p for p in result["panels"]}
    original = {p["panel_number"]: p for p in SAMPLE_SCENE["panels"]}

    for pn in (1, 3, 4):
        assert panels[pn]["dialogue"]           == original[pn]["dialogue"]
        assert panels[pn]["visual_description"] == original[pn]["visual_description"]
        assert panels[pn]["direction_note"]     == original[pn]["direction_note"]


# ---------------------------------------------------------------------------
# Contract 4 — safety guard: extra panels from Gemini are silently filtered
# ---------------------------------------------------------------------------

async def test_safety_guard_filters_unapproved_gemini_panels():
    """
    If Gemini returns revisions for panels [1, 2, 3] but only [1] is approved,
    panels 2 and 3 must NOT get new images — the safety guard filters them out.
    """
    gemini_returns_three = {
        "beat_map": {"tension": 90, "longing": 50, "resolve": 10},
        "revised_panels": [
            {
                "panel_number": 1, "visual_description": "Dark panel 1",
                "dialogue": "[SILENCE]", "direction_note": "Grim",
                "camera_angle": "Low angle", "image_prompt": "Dark 1",
            },
            {
                "panel_number": 2, "visual_description": "Extra panel 2",
                "dialogue": "Extra", "direction_note": "Extra",
                "camera_angle": "Wide", "image_prompt": "Extra 2",
            },
            {
                "panel_number": 3, "visual_description": "Extra panel 3",
                "dialogue": "Extra", "direction_note": "Extra",
                "camera_angle": "Close", "image_prompt": "Extra 3",
            },
        ],
    }

    with patch.object(agent, "_load_scene",      new_callable=AsyncMock, return_value=SAMPLE_SCENE), \
         patch.object(agent, "_call_gemini_json", new_callable=AsyncMock, return_value=json.dumps(gemini_returns_three)), \
         patch.object(agent, "_generate_image",   new_callable=AsyncMock, return_value="https://new/p1.png") as mock_imagen, \
         patch.object(agent, "_update_scene",     new_callable=AsyncMock):

        result = await agent.revise_scene(SAMPLE_SCENE["scene_id"], "darker", approved_panels=[1])

    # Imagen called once — only for approved panel 1
    assert mock_imagen.call_count == 1

    panels = {p["panel_number"]: p for p in result["panels"]}
    original = {p["panel_number"]: p for p in SAMPLE_SCENE["panels"]}

    # Panel 1 revised
    assert panels[1]["visual_description"] == "Dark panel 1"
    assert panels[1]["image_url"]          == "https://new/p1.png"

    # Panels 2, 3, 4 — completely untouched
    assert panels[2]["image_url"]          == original[2]["image_url"]
    assert panels[3]["image_url"]          == original[3]["image_url"]
    assert panels[4]["image_url"]          == original[4]["image_url"]


# ---------------------------------------------------------------------------
# Contract 5 — Imagen failure produces placeholder; scene still saves
# ---------------------------------------------------------------------------

async def test_imagen_failure_returns_placeholder_not_exception():
    """
    If _generate_image raises an exception internally, it catches it and returns
    a placehold.co URL.  The revision must still complete — scene still saved.
    """
    placeholder = "https://placehold.co/1280x720/1a1a1a/c9a84c?text=Panel+2"

    with patch.object(agent, "_load_scene",      new_callable=AsyncMock, return_value=SAMPLE_SCENE), \
         patch.object(agent, "_call_gemini_json", new_callable=AsyncMock, return_value=json.dumps(REVISION_PANEL_2_ONLY)), \
         patch.object(agent, "_generate_image",   new_callable=AsyncMock, return_value=placeholder), \
         patch.object(agent, "_update_scene",     new_callable=AsyncMock) as mock_update:

        result = await agent.revise_scene(SAMPLE_SCENE["scene_id"], "darker", approved_panels=[2])

    # Scene was saved despite placeholder
    mock_update.assert_called_once()

    panels = {p["panel_number"]: p for p in result["panels"]}
    assert "placehold.co" in panels[2]["image_url"]


# ---------------------------------------------------------------------------
# Contract 6 — beat map updated in Firestore after revision
# ---------------------------------------------------------------------------

async def test_revised_beat_map_saved_to_firestore():
    """
    The new beat map from Gemini's revision response must be what gets saved,
    not the original pre-revision beat map.
    """
    new_beat = {"tension": 92, "longing": 58, "resolve": 8}
    revision_resp = {
        "beat_map": new_beat,
        "revised_panels": [
            {
                "panel_number": 1, "visual_description": "Even darker.",
                "dialogue": "[SILENCE]", "direction_note": "Ominous",
                "camera_angle": "Dutch tilt", "image_prompt": "Dark 1",
            }
        ],
    }

    with patch.object(agent, "_load_scene",      new_callable=AsyncMock, return_value=SAMPLE_SCENE), \
         patch.object(agent, "_call_gemini_json", new_callable=AsyncMock, return_value=json.dumps(revision_resp)), \
         patch.object(agent, "_generate_image",   new_callable=AsyncMock, return_value="https://new/p1.png"), \
         patch.object(agent, "_update_scene",     new_callable=AsyncMock) as mock_update:

        result = await agent.revise_scene(SAMPLE_SCENE["scene_id"], "darker", approved_panels=[1])

    saved_args = mock_update.call_args.args
    saved_data = saved_args[1]   # second positional arg is the updates dict

    assert saved_data["beat_map"]["tension"] == 92
    assert saved_data["beat_map"]["longing"] == 58
    assert saved_data["beat_map"]["resolve"] == 8

    # Result returned to caller also reflects new beat map
    assert result["beat_map"]["tension"] == 92


# ---------------------------------------------------------------------------
# Contract 7 — approved_panels reflected in returned scene
# ---------------------------------------------------------------------------

async def test_affected_panels_recorded_in_result():
    """
    The returned scene must include `affected_panels` so the frontend can
    highlight which panels were regenerated.
    """
    with patch.object(agent, "_load_scene",      new_callable=AsyncMock, return_value=SAMPLE_SCENE), \
         patch.object(agent, "_call_gemini_json", new_callable=AsyncMock, return_value=json.dumps(REVISION_PANEL_2_ONLY)), \
         patch.object(agent, "_generate_image",   new_callable=AsyncMock, return_value="https://new/url.png"), \
         patch.object(agent, "_update_scene",     new_callable=AsyncMock):

        result = await agent.revise_scene(SAMPLE_SCENE["scene_id"], "darker", approved_panels=[2])

    assert result["affected_panels"] == [2]
