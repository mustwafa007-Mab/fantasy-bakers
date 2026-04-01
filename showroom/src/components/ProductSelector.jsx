import useShowroomStore from '../store/useShowroomStore';

// [AGENT NOTE]: ProductSelector — minimal UI owned by Cursor.
// Cursor will replace/extend this panel with the real 2D design.
// This stub is here so the scene is testable before the full UI arrives.

const PRODUCTS = [
  { key: 'bread',      label: '🍞 Bread Loaf',   color: '#d4a843' },
  { key: 'sugarRolls', label: '🍬 Sugar Rolls',  color: '#e87daa' },
  { key: 'buns',       label: '🫓 Buns',          color: '#c9763b' },
];

export default function ProductSelector() {
  const activeProduct = useShowroomStore((s) => s.activeProduct);
  const setProduct    = useShowroomStore((s) => s.setProduct);
  const meshLoaded    = useShowroomStore((s) => s.meshLoaded);
  const rotationDeg   = useShowroomStore((s) => s.rotationDeg);

  return (
    <div className="selector-panel">
      <div className="selector-title">Fantasy Bakery</div>
      <div className="selector-subtitle">3D Showroom</div>

      <div className="selector-buttons">
        {PRODUCTS.map(({ key, label, color }) => (
          <button
            key={key}
            className={`selector-btn ${activeProduct === key ? 'active' : ''}`}
            style={{ '--accent': color }}
            onClick={() => setProduct(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Engine status — reads Zustand state written by Antigravity */}
      <div className="selector-status">
        <span className={`status-dot ${meshLoaded ? 'loaded' : 'loading'}`} />
        {meshLoaded ? `Mesh ready · ${rotationDeg}°` : 'Loading model…'}
      </div>
    </div>
  );
}
