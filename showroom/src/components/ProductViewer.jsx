import { useRef, useEffect, Suspense } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import useShowroomStore from '../store/useShowroomStore';
import '../shaders/plasticWrap.glsl.js';

// [AGENT NOTE]: ProductViewer — Engine-owned. Loads GLB, animates rotation,
// applies plastic-wrap shader, writes meshLoaded + rotationDeg to store.

function ProductMesh({ modelPath }) {
  const meshRef      = useRef();
  const matRef       = useRef();
  const { scene }    = useGLTF(modelPath);
  const setMeshLoaded  = useShowroomStore((s) => s.setMeshLoaded);
  const setRotationDeg = useShowroomStore((s) => s.setRotationDeg);
  const setFacingCamera = useShowroomStore((s) => s.setFacingCamera);

  // Signal store as soon as mesh is ready
  useEffect(() => {
    setMeshLoaded(true);
  }, [modelPath, setMeshLoaded]);

  // 360° rotation + store sync
  useFrame((state, delta) => {
    if (!meshRef.current) return;

    meshRef.current.rotation.y += delta * 0.6;   // ~1 full rotation per 10s
    const deg = THREE.MathUtils.radToDeg(meshRef.current.rotation.y % (Math.PI * 2));
    setRotationDeg(Math.round(deg));

    // Animate shader time uniform
    if (matRef.current) {
      matRef.current.uTime = state.clock.elapsedTime;
    }

    // facingCamera: true while front face (−45° to 45°) is visible
    const yRad = ((meshRef.current.rotation.y % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
    setFacingCamera(yRad < Math.PI / 4 || yRad > (Math.PI * 7) / 4);
  });

  // Clone scene so useGLTF cache is not mutated
  const cloned = scene.clone(true);

  return (
    <group ref={meshRef} dispose={null}>
      {/* Original product mesh */}
      <primitive object={cloned} />

      {/* Plastic-wrap overlay on every child mesh */}
      {cloned.children.map((child, i) =>
        child.isMesh ? (
          <mesh
            key={i}
            geometry={child.geometry}
            position={child.position}
            rotation={child.rotation}
            scale={child.scale}
          >
            {/* [AGENT NOTE]: plasticWrapMat is the custom GLSL shaderMaterial */}
            <plasticWrapMat
              ref={matRef}
              transparent
              depthWrite={false}
              blending={THREE.AdditiveBlending}
            />
          </mesh>
        ) : null
      )}
    </group>
  );
}

// Fallback shown while GLB loads
function LoadingMesh() {
  const ref = useRef();
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.5;
  });
  return (
    <mesh ref={ref}>
      <torusKnotGeometry args={[0.6, 0.2, 64, 16]} />
      <meshStandardMaterial
        color="#d4a843"
        roughness={0.3}
        metalness={0.1}
        wireframe
      />
    </mesh>
  );
}

export default function ProductViewer() {
  const activeProduct   = useShowroomStore((s) => s.activeProduct);
  const PRODUCT_MODELS  = {
    bread:      '/models/bread.glb',
    sugarRolls: '/models/sugarRolls.glb',
    buns:       '/models/buns.glb',
  };
  const modelPath = PRODUCT_MODELS[activeProduct] ?? PRODUCT_MODELS.bread;

  return (
    <Suspense fallback={<LoadingMesh />}>
      <ProductMesh modelPath={modelPath} />
    </Suspense>
  );
}
