import ShowroomCanvas from './components/ShowroomCanvas';
import ProductSelector from './components/ProductSelector';

// [AGENT NOTE]: App.jsx — entry point. ShowroomCanvas (Engine) + ProductSelector (UI stub).
// Cursor will extend ProductSelector with the real 2D panel.

export default function App() {
  return (
    <div className="showroom-root">
      {/* Engine: Antigravity owns everything inside this canvas wrapper */}
      <div className="canvas-wrapper">
        <ShowroomCanvas />
      </div>

      {/* UI: Cursor extends this panel */}
      <ProductSelector />
    </div>
  );
}
