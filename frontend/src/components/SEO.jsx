import React from 'react'
import { Helmet } from 'react-helmet-async'

const SITE_URL = 'https://cadence-ci.com'
const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`

export default function SEO({
  title,
  description,
  path = '',
  image = DEFAULT_OG_IMAGE,
  noindex = false,
}) {
  const fullTitle = title
    ? `${title} | Cadence Catalog Intelligence`
    : 'Cadence Catalog Intelligence — Music Catalog Valuation, Rights & Revenue Platform'
  const url = `${SITE_URL}${path}`

  return (
    <Helmet>
      <title>{fullTitle}</title>
      {description && <meta name="description" content={description} />}
      <link rel="canonical" href={url} />
      {noindex && <meta name="robots" content="noindex, nofollow" />}

      <meta property="og:title" content={fullTitle} />
      {description && <meta property="og:description" content={description} />}
      <meta property="og:url" content={url} />
      <meta property="og:image" content={image} />
      <meta property="og:type" content="website" />

      <meta name="twitter:title" content={fullTitle} />
      {description && <meta name="twitter:description" content={description} />}
      <meta name="twitter:image" content={image} />
      <meta name="twitter:card" content="summary_large_image" />
    </Helmet>
  )
}
