const CUTS = [
  { icon: "🌑", label: "Make it darker",    note: "make it darker and more ominous" },
  { icon: "🌅", label: "Add hope",          note: "add a glimmer of hope and warmth" },
  { icon: "💔", label: "More longing",      note: "amplify the longing and yearning" },
  { icon: "⚡", label: "Raise tension",     note: "raise the tension to a breaking point" },
  { icon: "🤫", label: "Cut to silence",    note: "cut to silence — strip away dialogue" },
  { icon: "🐌", label: "Slow it down",      note: "slow the pace — meditative, deliberate" },
  { icon: "🔥", label: "Burn it down",      note: "burn it down — raw, visceral, chaotic" },
  { icon: "🌊", label: "Flood with grief",  note: "flood the scene with grief and loss" },
];

export default function QuickCuts({ onRevise, isRevising }) {
  return (
    <div className="quick-cuts-card">
      <div className="card-title">⚡ Quick Cuts</div>
      <div className="quick-cuts-grid">
        {CUTS.map(({ icon, label, note }) => (
          <button
            key={label}
            className="quick-cut-btn"
            disabled={isRevising}
            onClick={() => onRevise(note)}
            title={note}
          >
            <span className="icon">{icon}</span>
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
