import { Canvas } from '@react-three/fiber';
import { Environment, OrbitControls, ContactShadows } from '@react-three/drei';
import ProductViewer from './ProductViewer';
import CanvasErrorBoundary from './CanvasErrorBoundary';

// [AGENT NOTE]: ShowroomCanvas — Engine-owned. Antigravity controls everything
// inside this <Canvas />. Cursor does NOT modify this file.

export default function ShowroomCanvas() {
  return (
    <CanvasErrorBoundary>
    <Canvas
      shadows
      camera={{ position: [0, 0.5, 3.5], fov: 40 }}
      gl={{ antialias: true, alpha: false }}
      style={{ background: 'transparent' }}
    >
      {/* Ambient fill */}
      <ambientLight intensity={0.4} />

      {/* Key light — warm from top-left */}
      <directionalLight
        position={[4, 6, 3]}
        intensity={1.8}
        castShadow
        shadow-mapSize={[2048, 2048]}
        color="#fff8e7"
      />

      {/* Rim light — cool from behind */}
      <pointLight position={[-3, 2, -4]} intensity={1.2} color="#a8d8ea" />

      {/* HDRI environment for reflections */}
      <Environment preset="studio" />

      {/* Product model with plastic-wrap shader + rotation */}
      <ProductViewer />

      {/* Soft ground shadow */}
      <ContactShadows
        position={[0, -1.2, 0]}
        opacity={0.45}
        scale={5}
        blur={2.5}
        far={4}
      />

      {/* Manual inspection via drag */}
      <OrbitControls
        enablePan={false}
        minDistance={2}
        maxDistance={6}
        minPolarAngle={Math.PI / 6}
        maxPolarAngle={Math.PI / 1.8}
        enableDamping
        dampingFactor={0.05}
      />
    </Canvas>
    </CanvasErrorBoundary>
  );
}
