import { useState } from 'react'
import { Download } from 'lucide-react'

const LABELS = {
  protan: { title: 'Protan', cone: 'L', border: 'border-rose-300' },
  deutan: { title: 'Deutan', cone: 'M', border: 'border-emerald-300' },
}
const pct = (value) => `${(value * 100).toFixed(2)}%`

export default function SimulationResults({ analysis }) {
  const [family, setFamily] = useState('protan')
  const [severity, setSeverity] = useState(1)
  const items = analysis.results.filter((item) => item.cvdType === family)
  const selected = items.find((item) => item.severity === severity) ?? items[0]
  const label = LABELS[family]

  function download() {
    const link = document.createElement('a')
    link.href = selected.image
    link.download = `simulasi_${family}_${severity * 100}.png`
    link.click()
  }

  return (
    <section className="space-y-6" aria-labelledby="results-title">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-primary">Hasil eksperimen</p>
          <h2 id="results-title" className="text-3xl font-black">Perbandingan empat severity</h2>
        </div>
        <div className="flex rounded-xl bg-surface-container p-1">
          {Object.entries(LABELS).map(([key, value]) => (
            <button key={key} type="button" onClick={() => setFamily(key)} className={`rounded-lg px-4 py-2 text-sm font-bold ${family === key ? 'bg-white text-primary shadow-sm' : ''}`}>
              {value.title}
            </button>
          ))}
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-5">
        <article className="rounded-3xl border bg-white p-3">
          <p className="mb-2 text-sm font-bold">Citra asli</p>
          <img src={analysis.original} alt="Citra asli" className="aspect-square w-full rounded-2xl bg-surface-container object-contain" />
        </article>
        <div className="grid gap-3 sm:grid-cols-2 lg:col-span-4 lg:grid-cols-4">
          {items.map((item) => (
            <button key={item.severity} type="button" onClick={() => setSeverity(item.severity)} className={`rounded-3xl border-2 bg-white p-3 text-left ${selected.severity === item.severity ? label.border : 'border-transparent'}`}>
              <p className="mb-2 font-black">{item.severity * 100}% severity</p>
              <img src={item.image} alt={`Simulasi ${label.title} ${item.severity * 100}%`} className="aspect-square w-full rounded-2xl bg-surface-container object-contain" />
              <dl className="mt-3 space-y-1 text-xs">
                <div className="flex justify-between font-bold"><dt>Rata-rata ΔE00</dt><dd>{item.metrics.meanDeltaE00.toFixed(4)}</dd></div>
                <div className="flex justify-between"><dt>Perubahan RGB</dt><dd>{pct(item.metrics.meanAbsRgbChange)}</dd></div>
                <div className="flex justify-between"><dt>Piksel berubah</dt><dd>{pct(item.metrics.changedPixelRatio)}</dd></div>
              </dl>
            </button>
          ))}
        </div>
      </div>

      <figure className="grid gap-6 rounded-3xl border bg-white p-5 md:grid-cols-2" aria-labelledby="heatmap-title">
        <img src={selected.deltaE00Heatmap} alt={`Peta perbedaan warna ΔE00 ${label.title}, severity ${selected.severity * 100}%`} className="aspect-square max-h-[20rem] w-full rounded-2xl object-contain" />
        <figcaption className="space-y-4 self-center">
          <h3 id="heatmap-title" className="text-xl font-black">Heatmap ΔE00: {label.title} {selected.severity * 100}%</h3>
          <p className="text-md text-on-surface-variant">Setiap piksel dibandingkan dengan posisi yang sama pada citra asli. Ungu menunjukkan perbedaan kecil dan kuning menunjukkan perbedaan besar.</p>
          <p className="text-lg font-bold">Rata-rata ΔE00: {selected.metrics.meanDeltaE00.toFixed(4)}</p>
          <div aria-label={`Skala ΔE00 dari 0 sampai ${analysis.heatmapScale.max.toFixed(4)}`}>
            <div className="h-4 rounded-full" style={{ background: 'linear-gradient(to right, #440154, #3b528b, #21918c, #5ec962, #fde725)' }} />
            <div className="mt-1 flex justify-between text-normal"><span>0</span><span>{analysis.heatmapScale.max.toFixed(4)} ΔE00</span></div>
          </div>
          {analysis.heatmapScale.max === 0 && <p className="text-md">Seluruh kondisi memiliki ΔE00 nol. Heatmap ditampilkan dengan warna minimum.</p>}
          {/* <a href={selected.deltaE00Heatmap} download={`heatmap_${family}_${selected.severity * 100}.png`} className="inline-flex items-center gap-2 text-sm font-bold text-primary"><Download size={16} /> Unduh heatmap</a> */}
        </figcaption>
      </figure>

      <div className="grid gap-4 rounded-3xl border bg-white p-5 lg:grid-cols-[1fr_1.5fr_auto]">
        <div><p className="text-sm text-on-surface-variant">Kondisi terpilih</p><h3 className="text-xl font-black">{label.title} {severity * 100}%</h3></div>
        <div><p className="mb-2 text-sm font-bold">Matriks aktif</p><div className="grid grid-cols-3 gap-1 font-mono text-xs">{selected.matrix.flat().map((value, index) => <span key={index} className="rounded bg-surface-container p-1 text-center">{value.toFixed(4)}</span>)}</div></div>
        <button type="button" onClick={download} className="flex items-center justify-center gap-2 self-center rounded-xl bg-primary px-4 py-3 font-bold text-white"><Download size={18} /> Unduh</button>
      </div>
    </section>
  )
}

