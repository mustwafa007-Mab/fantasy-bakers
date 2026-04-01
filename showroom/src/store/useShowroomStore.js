import { create } from 'zustand';

// [AGENT NOTE]: This store is the ONLY cross-boundary state layer.
// Antigravity (Engine) writes: meshLoaded, rotationDeg, facingCamera
// Cursor (UI) writes: activeProduct
// Neither agent touches the other's primary domain directly.

const PRODUCT_MODELS = {
  bread:      '/models/bread.glb',
  sugarRolls: '/models/sugarRolls.glb',
  buns:       '/models/buns.glb',
};

const useShowroomStore = create((set) => ({
  // --- UI State (Cursor owns writes) ---
  activeProduct: 'bread',           // 'bread' | 'sugarRolls' | 'buns'

  // --- Engine State (Antigravity owns writes) ---
  meshLoaded:   false,
  rotationDeg:  0,
  facingCamera: true,

  // --- Derived ---
  get activeModelPath() {
    return PRODUCT_MODELS[this.activeProduct] ?? PRODUCT_MODELS.bread;
  },

  // --- Actions ---
  setProduct: (product) => set({
    activeProduct: product,
    meshLoaded:    false,   // reset while new model loads
    rotationDeg:   0,
  }),

  setMeshLoaded:   (v)   => set({ meshLoaded:   v }),
  setRotationDeg:  (deg) => set({ rotationDeg:  deg }),
  setFacingCamera: (v)   => set({ facingCamera: v }),
}));

export { PRODUCT_MODELS };
export default useShowroomStore;
