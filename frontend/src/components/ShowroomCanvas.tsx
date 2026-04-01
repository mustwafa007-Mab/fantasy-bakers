import { Canvas } from '@react-three/fiber'
import type { ReactNode } from 'react'

type Props = {
  /** Antigravity supplies the R3F scene graph as children. Until then, leave empty. */
  children?: ReactNode
}

/**
 * Shell only: R3F Canvas + camera defaults. No meshes, lights, or loaders here — Engine owns those.
 */
export function ShowroomCanvas({ children }: Props) {
  return (
    <div className="showroom-canvas-wrap" data-testid="showroom-canvas">
      <Canvas
        shadows
        camera={{ position: [0, 0.5, 3.2], fov: 42 }}
        gl={{ antialias: true, alpha: true }}
      >
        {/* [AGENT NOTE]: All Three/R3F scene content (lights, GLB, materials, useFrame) lives in Engine-owned modules passed as `children` or composed here by Antigravity. */}
        {children}
      </Canvas>
    </div>
  )
}
