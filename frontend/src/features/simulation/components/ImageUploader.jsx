import { useRef, useState } from 'react'
import { CheckCircle2, ImagePlus } from 'lucide-react'

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_BYTES = 10 * 1024 * 1024

export default function ImageUploader({ onSelect }) {
  const inputRef = useRef(null)
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  function choose(file) {
    if (!file) return
    if (!ACCEPTED_TYPES.includes(file.type) || file.size > MAX_BYTES) {
      setError('Gambar tidak sesuai ketentuan')
      return
    }
    setError('')
    setName(file.name)
    onSelect(file)
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()
          choose(event.dataTransfer.files?.[0])
        }}
        className="flex min-h-44 w-full flex-col items-center justify-center gap-3 rounded-3xl border-2 border-dashed border-outline-variant bg-white p-6 text-center transition hover:border-primary hover:bg-primary/5"
      >
        {name ? <CheckCircle2 className="text-primary" size={36} /> : <ImagePlus className="text-primary" size={36} />}
        <span className="text-lg font-bold">{name || 'Pilih gambar'}</span>
        <span className="text-sm text-on-surface-variant">JPG, PNG, atau WebP, maksimum 10 MB</span>
      </button>
      <input ref={inputRef} hidden type="file" accept=".jpg,.jpeg,.png,.webp" onChange={(event) => choose(event.target.files?.[0])} />
      {error && <p className="mt-2 text-sm font-medium text-error">{error}</p>}
    </div>
  )
}

