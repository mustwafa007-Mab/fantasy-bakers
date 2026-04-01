import type { ShowcaseProductDTO } from '../store/showcaseStore'

export async function fetchShowcaseProduct(): Promise<ShowcaseProductDTO> {
  const res = await fetch('/api/showcase/product')
  if (!res.ok) {
    throw new Error(`Showcase API ${res.status}`)
  }
  return res.json() as Promise<ShowcaseProductDTO>
}
