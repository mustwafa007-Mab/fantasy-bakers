import { useEffect } from 'react'
import { fetchShowcaseProduct } from '../api/showcase'
import { useShowcaseStore } from '../store/showcaseStore'

export function ProductPanel() {
  const productName = useShowcaseStore((s) => s.productName)
  const priceKes = useShowcaseStore((s) => s.priceKes)
  const whatsappHref = useShowcaseStore((s) => s.whatsappHref)
  const productLoading = useShowcaseStore((s) => s.productLoading)
  const productError = useShowcaseStore((s) => s.productError)
  const meshLoaded = useShowcaseStore((s) => s.meshLoaded)
  const hydrateProductFromApi = useShowcaseStore((s) => s.hydrateProductFromApi)
  const setProductLoading = useShowcaseStore((s) => s.setProductLoading)
  const setProductError = useShowcaseStore((s) => s.setProductError)

  useEffect(() => {
    let cancelled = false
    setProductLoading(true)
    fetchShowcaseProduct()
      .then((dto) => {
        if (!cancelled) hydrateProductFromApi(dto)
      })
      .catch(() => {
        if (!cancelled) setProductError('Could not load product from server.')
      })
    return () => {
      cancelled = true
    }
  }, [hydrateProductFromApi, setProductLoading, setProductError])

  return (
    <aside className="product-panel">
      <p className="product-panel__eyebrow">Fantasy Bakery · 3D showroom</p>
      <h1 className="product-panel__title">{productLoading ? 'Loading…' : productName}</h1>
      {!productLoading && !productError && (
        <p className="product-panel__price">
          <span className="product-panel__price-value">KES {priceKes.toLocaleString('en-KE')}</span>
        </p>
      )}
      {productError && <p className="product-panel__error">{productError}</p>}
      <a
        className="product-panel__cta"
        href={productLoading || productError ? undefined : whatsappHref}
        target="_blank"
        rel="noopener noreferrer"
        aria-disabled={productLoading || !!productError}
        onClick={(e) => {
          if (productLoading || productError) e.preventDefault()
        }}
      >
        Order on WhatsApp
      </a>
      <p className="product-panel__meta" aria-live="polite">
        3D model: {meshLoaded ? 'ready' : 'loading…'}
      </p>
    </aside>
  )
}
