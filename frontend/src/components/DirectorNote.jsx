import { useState } from "react";

export default function DirectorNote({ onPreview, isPreviewing }) {
  const [note, setNote] = useState("");

  const handleSubmit = () => {
    if (!note.trim() || isPreviewing) return;
    onPreview(note.trim());
    setNote("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmit();
  };

  return (
    <div className="director-note-card">
      <div className="card-title">✏ Director&apos;s Note</div>

      <div className="note-input-wrap">
        <textarea
          className="note-input"
          placeholder={
            isPreviewing
              ? "Fetching proposal…"
              : 'e.g. "make it darker", "add a ghost in panel 2", "cut the dialogue"'
          }
          value={note}
          onChange={(e) => setNote(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isPreviewing}
          rows={3}
        />
      </div>

      <div className="note-submit-row">
        <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
          ⌘↵ to preview
        </span>
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={!note.trim() || isPreviewing}
        >
          {isPreviewing ? (
            <><span className="spinner" /> Analyzing…</>
          ) : (
            <>Preview Changes →</>
          )}
        </button>
      </div>
    </div>
  );
}
