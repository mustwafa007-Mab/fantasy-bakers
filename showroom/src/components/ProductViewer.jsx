import { useRef, useEffect, Suspense } from 'react';
import { useFrame } from '@react-three/fiber';
import { RoundedBox, useTexture } from '@react-three/drei';
import * as THREE from 'three';
import useShowroomStore from '../store/useShowroomStore';

// [AGENT NOTE]: ProductViewer — Engine-owned. Uses Procedural Geometry (RoundedBox)
// and loads highly-optimized WebP PBR textures (Albedo, Roughness, Displacement).

function ProductMesh() {
  const meshRef = useRef();
  const setMeshLoaded = useShowroomStore((s) => s.setMeshLoaded);
  const setRotationDeg = useShowroomStore((s) => s.setRotationDeg);
  const setFacingCamera = useShowroomStore((s) => s.setFacingCamera);
  const activeProduct = useShowroomStore((s) => s.activeProduct);

  // Load PBR Textures (WebP compressed via Antigravity)
  const props = useTexture({
    map: '/textures/bread/front_albedo.webp',
    displacementMap: '/textures/bread/front_displacement.webp',
    roughnessMap: '/textures/bread/front_roughness.webp',
  });

  // Signal store when textures and geometry are fully mounted
  useEffect(() => {
    setMeshLoaded(true);
  }, [setMeshLoaded]);

  // Rotate slowly on the Y axis
  useFrame((_, delta) => {
    if (!meshRef.current) return;
    
    // Slow cinematic rotation
    meshRef.current.rotation.y += delta * 0.4;
    
    // Update store state for UI linkage
    const yRad = ((meshRef.current.rotation.y % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
    const deg = THREE.MathUtils.radToDeg(yRad);
    setRotationDeg(Math.round(deg));
    setFacingCamera(yRad < Math.PI / 4 || yRad > (Math.PI * 7) / 4);
  });

  // Dimensions based on product type
  let args = [2.2, 1.2, 1.2]; // Default: Bread Loaf dimensions
  if (activeProduct === 'sugarRolls') args = [1.8, 0.4, 2.0]; // Packs are wider/flatter
  if (activeProduct === 'buns') args = [1.5, 0.5, 1.5]; // Square-ish pack

  // Fix UV stretch on displacement by scaling it down slightly
  const displacementScale = activeProduct === 'sugarRolls' ? 0.08 : 0.03;

  return (
    <mesh ref={meshRef} castShadow receiveShadow position={[0, 0.6, 0]}>
      {/* Procedural Filleted Box */}
      <RoundedBox args={args} radius={0.15} smoothness={4}>
        <meshStandardMaterial
          {...props}
          displacementScale={displacementScale}
          color="#ffffff"
          envMapIntensity={1.5} /* Boost HDRI reflections for the plastic wrap */
        />
      </RoundedBox>
    </mesh>
  );
}

// Fallback shown while Textures load
function LoadingMesh() {
  const ref = useRef();
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.x += delta;
  });
  return (
    <mesh ref={ref} position={[0, 0.6, 0]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="#5e2a84" wireframe />
    </mesh>
  );
}

export default function ProductViewer() {
  return (
    <Suspense fallback={<LoadingMesh />}>
      <ProductMesh />
    </Suspense>
  );
}
