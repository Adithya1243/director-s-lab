const BEATS = [
  { key: "tension", label: "Tension", cls: "tension" },
  { key: "longing",  label: "Longing",  cls: "longing"  },
  { key: "resolve",  label: "Resolve",  cls: "resolve"  },
];

function arcDescription(beatMap) {
  const { tension, longing, resolve } = beatMap;
  const max = Math.max(tension, longing, resolve);
  if (max === tension) return "High-stakes confrontation arc";
  if (max === longing)  return "Aching desire arc";
  return "Redemptive resolve arc";
}

export default function BeatMap({ beatMap }) {
  if (!beatMap) return null;

  return (
    <div className="beat-map-card fade-in">
      <div className="card-title">
        ◈ Beat Map
        <span className="beat-arc-label">{arcDescription(beatMap)}</span>
      </div>
      <div className="beat-bars">
        {BEATS.map(({ key, label, cls }) => (
          <div className="beat-row" key={key}>
            <div className="beat-label-row">
              <span className="beat-label" style={{ color: `var(--${cls}-color)` }}>
                {label}
              </span>
              <span className="beat-value">{beatMap[key]}</span>
            </div>
            <div className="beat-track">
              <div
                className={`beat-fill ${cls}`}
                style={{ width: `${beatMap[key]}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
