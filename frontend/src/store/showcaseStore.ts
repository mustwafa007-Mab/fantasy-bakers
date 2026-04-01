import { create } from 'zustand'

/** Payload from `GET /api/showcase/product` — owned by FastAPI; shape should stay in sync. */
export type ShowcaseProductDTO = {
  name: string
  price_kes: number
  whatsapp_e164: string
  whatsapp_message: string
}

type SceneBridgeSlice = {
  meshLoaded: boolean
  rotationDeg: number
  facingCamera: boolean
  /** [AGENT NOTE]: Engine (Antigravity) should call only this action for scene→UI state — no React props. */
  setSceneBridge: (
    partial: Partial<Pick<SceneBridgeSlice, 'meshLoaded' | 'rotationDeg' | 'facingCamera'>>,
  ) => void
}

type ShowcaseUISlice = {
  productName: string
  priceKes: number
  whatsappHref: string
  productLoading: boolean
  productError: string | null
  hydrateProductFromApi: (dto: ShowcaseProductDTO) => void
  setProductLoading: (v: boolean) => void
  setProductError: (msg: string | null) => void
}

export type ShowcaseState = SceneBridgeSlice & ShowcaseUISlice

function buildWhatsAppHref(e164: string, message: string): string {
  const digits = e164.replace(/\D/g, '')
  const q = encodeURIComponent(message)
  return `https://wa.me/${digits}?text=${q}`
}

export const useShowcaseStore = create<ShowcaseState>((set) => ({
  meshLoaded: false,
  rotationDeg: 0,
  facingCamera: true,
  setSceneBridge: (partial) => set(partial),

  productName: '…',
  priceKes: 0,
  whatsappHref: '',
  productLoading: true,
  productError: null,
  hydrateProductFromApi: (dto) =>
    set({
      productName: dto.name,
      priceKes: dto.price_kes,
      whatsappHref: buildWhatsAppHref(dto.whatsapp_e164, dto.whatsapp_message),
      productLoading: false,
      productError: null,
    }),
  setProductLoading: (v) => set({ productLoading: v }),
  setProductError: (msg) => set({ productError: msg, productLoading: false }),
}))
