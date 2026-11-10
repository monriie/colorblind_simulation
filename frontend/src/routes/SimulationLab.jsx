import { useState } from "react";
import { FlaskConical, Play, RotateCcw } from "lucide-react";
import ImageUploader from "@/features/simulation/components/ImageUploader.jsx";
import SimulationResults from "@/features/simulation/components/SimulationResults.jsx";
import { useAnalyzeSimulation } from "@/features/simulation/hooks/useAnalyzeSimulation.js";
import Button from "@/shared/components/Button.jsx";
import InfoBanner from "@/shared/components/InfoBanner.jsx";

export default function SimulationLab() {
  const [file, setFile] = useState(null);
  const [uploadKey, setUploadKey] = useState(0);
  const simulation = useAnalyzeSimulation();

  function run() {
    if (file) simulation.mutate(file);
  }

  function reset() {
    setFile(null);
    simulation.reset();
    setUploadKey((current) => current + 1);
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-outline-variant bg-white/90">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="rounded-xl bg-primary p-2 text-white">
              <FlaskConical />
            </span>
            <div>
              <p className="font-black">Machado CVD Lab</p>
            </div>
          </div>
          {/* <button
            type="button"
            onClick={() => document.documentElement.requestFullscreen?.()}
            className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold"
          >
            <Maximize2 size={16} /> Mode presentasi
          </button> */}
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-10 px-5 py-10">
        <section className="grid items-center gap-8 lg:grid-cols-2">
          <div>
            <p className="mb-3 font-bold text-4xl uppercase tracking-[0.24em] text-primary">
              Simulasi color vision deficiency
            </p>
            {/* <h1 className="max-w-3xl text-4xl font-black leading-tight sm:text-6xl">
              Satu citra, delapan kondisi, satu engine penelitian.
            </h1> */}
            <p className="mt-5 max-w-2xl text-lg leading-relaxed text-on-surface-variant">
              Bandingkan protan dan deutan pada severity 25%, 50%, 75%, dan
              100%.
            </p>
          </div>
          <section className="grid grid-cols-2 gap-3 rounded-[2rem] bg-surface-container-low p-5 lg:grid-cols-[1fr_auto] lg:items-end">
            <ImageUploader key={uploadKey} onSelect={setFile} />
            <div className="flex gap-3 lg:flex-col">
              <Button
                onClick={run}
                disabled={!file || simulation.isPending}
                className="flex flex-1 items-center justify-center gap-2"
              >
                <Play size={18} />{" "}
                {simulation.isPending
                  ? "Menjalankan 8 simulasi..."
                  : "Jalankan simulasi"}
              </Button>
              <Button
                variant="secondary"
                onClick={reset}
                disabled={!simulation.data || simulation.isPending}
                className="flex items-center justify-center gap-2"
              >
                <RotateCcw size={18} /> Reset
              </Button>
            </div>
          </section>
        </section>

        {simulation.isError && (
          <InfoBanner variant="warning">
            Gagal memproses citra: {simulation.error.message}
          </InfoBanner>
        )}
        {simulation.data && <SimulationResults analysis={simulation.data} />}
      </div>
    </main>
  );
}
