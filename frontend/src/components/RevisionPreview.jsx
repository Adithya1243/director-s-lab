import { useState, useRef } from "react";

const BEAT_META = {
  tension: { label: "Tension", color: "var(--tension-color)" },
  longing:  { label: "Longing",  color: "var(--longing-color)"  },
  resolve:  { label: "Resolve",  color: "var(--resolve-color)"  },
};

function BeatDiff({ label, color, before, after }) {
  const delta = after - before;
  const sign  = delta > 0 ? "+" : "";
  const deltaColor = delta > 0 ? "#e0b450" : delta < 0 ? "#e06060" : "var(--text-muted)";

  return (
    <div className="beat-diff-row">
      <span className="beat-diff-label" style={{ color }}>{label}</span>
      <div className="beat-diff-bars">
        <div className="beat-diff-track">
          <div className="beat-diff-fill before" style={{ width: `${before}%`, background: color + "55" }} />
        </div>
        <div className="beat-diff-track">
          <div className="beat-diff-fill after" style={{ width: `${after}%`, background: color }} />
        </div>
      </div>
      <span className="beat-diff-delta" style={{ color: deltaColor }}>
        {sign}{delta}
      </span>
    </div>
  );
}

function formatTime(secs) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function RevisionPreview({ proposal, panels, onConfirm, onCancel, isApplying }) {
  const { revision_note, current_beat_map, proposed_beat_map, beat_map_rationale, proposed_panels } = proposal;

  // Map panel_number → panel (for video_url lookup)
  const panelMap = Object.fromEntries((panels || []).map((p) => [p.panel_number, p]));

  // Default: all proposed panels checked
  const [checked, setChecked] = useState(
    () => new Set(proposed_panels.map((p) => p.panel_number))
  );

  // Video timestamp markers: {panel_number: seconds}
  const [timestamps, setTimestamps] = useState({});
  const videoRefs = useRef({});
  const [expandedVideos, setExpandedVideos] = useState(new Set());

  const toggle = (num) => {
    setChecked((prev) => {
      const next = new Set(prev);
      next.has(num) ? next.delete(num) : next.add(num);
      return next;
    });
  };

  const toggleVideoExpand = (num) => {
    setExpandedVideos((prev) => {
      const next = new Set(prev);
      next.has(num) ? next.delete(num) : next.add(num);
      return next;
    });
  };

  const markTimestamp = (panelNum) => {
    const vid = videoRefs.current[panelNum];
    if (vid) {
      setTimestamps((prev) => ({ ...prev, [panelNum]: Math.floor(vid.currentTime) }));
    }
  };

  const approvedList = [...checked].sort((a, b) => a - b);
  const noneSelected = approvedList.length === 0;

  return (
    <div className="revision-preview-overlay fade-in">
      <div className="revision-preview-card">
        {/* Header */}
        <div className="rp-header">
          <div className="rp-title">🎬 Revision Proposal</div>
          <div className="rp-note">"{revision_note}"</div>
        </div>

        {/* Beat map diff */}
        <div className="rp-section">
          <div className="rp-section-label">Beat Map Changes</div>
          <div className="beat-diff-grid">
            {Object.entries(BEAT_META).map(([key, { label, color }]) => (
              <BeatDiff
                key={key}
                label={label}
                color={color}
                before={current_beat_map[key]}
                after={proposed_beat_map[key]}
              />
            ))}
          </div>
          {beat_map_rationale && (
            <p className="rp-rationale">↳ {beat_map_rationale}</p>
          )}
        </div>

        {/* Panel proposals */}
        <div className="rp-section">
          <div className="rp-section-label">
            Panels to Revise
            <span className="rp-section-hint"> — toggle to include or exclude</span>
          </div>
          <div className="rp-panels">
            {proposed_panels.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: 12 }}>
                No panel changes proposed for this note.
              </p>
            ) : (
              proposed_panels.map((p) => {
                const scenePanel = panelMap[p.panel_number];
                const hasVideo   = Boolean(scenePanel?.video_url);
                const isExpanded = expandedVideos.has(p.panel_number);
                const ts         = timestamps[p.panel_number];

                return (
                  <div
                    key={p.panel_number}
                    className={`rp-panel-row ${checked.has(p.panel_number) ? "selected" : "deselected"}`}
                  >
                    <label className="rp-panel-toggle">
                      <input
                        type="checkbox"
                        className="rp-checkbox"
                        checked={checked.has(p.panel_number)}
                        onChange={() => toggle(p.panel_number)}
                        disabled={isApplying}
                      />
                      <div className="rp-panel-info">
                        <div className="rp-panel-head">
                          <span className="rp-panel-num">Panel {p.panel_number}</span>
                          <span className={`rp-change-badge ${p.change_type}`}>
                            {p.change_type === "add_element" ? "+ add element" : "↻ revise"}
                          </span>
                        </div>
                        <p className="rp-panel-reason">{p.reason}</p>
                        <p className="rp-panel-summary">{p.change_summary}</p>
                      </div>
                    </label>

                    {/* Video timestamp picker — only for panels with a video clip */}
                    {hasVideo && (
                      <div className="rp-video-section">
                        <button
                          className="btn btn-ghost rp-video-toggle"
                          onClick={() => toggleVideoExpand(p.panel_number)}
                          disabled={isApplying}
                        >
                          🎥 {isExpanded ? "Hide clip" : "Pick a moment"}
                          {ts !== undefined && (
                            <span className="rp-ts-badge">⏱ {formatTime(ts)}</span>
                          )}
                        </button>
                        {isExpanded && (
                          <div className="rp-video-player">
                            <video
                              ref={(el) => { if (el) videoRefs.current[p.panel_number] = el; }}
                              src={scenePanel.video_url}
                              controls
                              playsInline
                              preload="metadata"
                              className="rp-video"
                            />
                            <button
                              className="btn btn-ghost rp-mark-btn"
                              onClick={() => markTimestamp(p.panel_number)}
                              disabled={isApplying}
                            >
                              📍 Mark this moment
                              {ts !== undefined && ` — currently ${formatTime(ts)}`}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="rp-actions">
          <button className="btn btn-ghost" onClick={onCancel} disabled={isApplying}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={() => onConfirm(approvedList, timestamps)}
            disabled={noneSelected || isApplying}
            title={noneSelected ? "Select at least one panel" : ""}
          >
            {isApplying ? (
              <><span className="spinner" /> Generating {approvedList.length} panel{approvedList.length !== 1 ? "s" : ""}…</>
            ) : (
              <>Apply {approvedList.length} Panel{approvedList.length !== 1 ? "s" : ""} →</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
