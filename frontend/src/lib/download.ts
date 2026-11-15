/** Save JSON as a file in the browser (no server round-trip). */
export function downloadJson(data: unknown, filename: string, mime = 'application/json'): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
