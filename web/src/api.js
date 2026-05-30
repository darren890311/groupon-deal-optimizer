const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8080'

export async function analyzeDeal(url) {
  const res = await fetch(`${API_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })

  let data = null
  try {
    data = await res.json()
  } catch {
    // non-JSON error body
  }

  if (!res.ok) {
    const msg = data?.error || data?.detail || `Request failed (${res.status})`
    throw new Error(msg)
  }
  return data
}

// Where "Book anyway" links to. Centralized so swapping the raw deal URL for a
// Groupon affiliate link later is a one-line change.
export function bookingUrl(dealUrl) {
  // TODO: wrap with the Groupon affiliate redirect/params once enrolled.
  return dealUrl
}
