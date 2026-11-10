import { API_BASE_URL } from '@/shared/lib/apiClient.js'

export async function analyzeSimulation(image) {
  const formData = new FormData()
  formData.append('image', image)
  const response = await fetch(`${API_BASE_URL}/api/simulation/analyze`, {
    method: 'POST',
    body: formData,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Request gagal: ${response.status}`)
  }
  return response.json()
}

