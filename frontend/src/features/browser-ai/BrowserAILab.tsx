import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "../../shared/ui/Button";
import { benchmarkCases, evaluateBenchmarkResult } from "./benchmark";
import { canRunBrowserAI, detectBrowserCapabilities } from "./capabilities";
import { browserAIModels, findBrowserAIModel, formatBytes } from "./catalog";
import { createBrowserAIClient, type BrowserAIClient } from "./client";
import type { BenchmarkResult, BrowserCapabilities } from "./types";

type LabState = "checking" | "idle" | "loading" | "ready" | "benchmarking" | "error";

export function BrowserAILab() {
  const [capabilities, setCapabilities] = useState<BrowserCapabilities>();
  const [selectedId, setSelectedId] = useState<string>(browserAIModels[0].id);
  const [consented, setConsented] = useState(false);
  const [state, setState] = useState<LabState>("checking");
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState("Checking browser capabilities");
  const [results, setResults] = useState<readonly BenchmarkResult[]>([]);
  const clientRef = useRef<BrowserAIClient | undefined>(undefined);
  const selectedModel = useMemo(() => findBrowserAIModel(selectedId) ?? browserAIModels[0], [selectedId]);

  useEffect(() => {
    let active = true;
    void detectBrowserCapabilities().then((detected) => {
      if (!active) return;
      setCapabilities(detected);
      setState("idle");
      setProgressLabel(canRunBrowserAI(detected) ? "Browser is ready" : "WebGPU is unavailable");
    });
    return () => {
      active = false;
      void clientRef.current?.dispose();
    };
  }, []);

  const supported = capabilities ? canRunBrowserAI(capabilities) : false;

  async function loadModel() {
    setState("loading");
    setResults([]);
    setProgress(0);
    const previousClient = clientRef.current;
    clientRef.current = undefined;
    await previousClient?.dispose().catch(() => undefined);
    const client = createBrowserAIClient();
    clientRef.current = client;
    try {
      await client.load(selectedModel, (event) => {
        setProgress(event.progress);
        setProgressLabel(event.message);
      });
      setState("ready");
      setProgress(1);
      setProgressLabel(`${selectedModel.name} ready in this browser`);
    } catch {
      setState("error");
      setProgressLabel("The local runtime could not load this model");
    }
  }

  async function runBenchmark() {
    const client = clientRef.current;
    if (!client) return;
    setState("benchmarking");
    setResults([]);
    try {
      const measured: BenchmarkResult[] = [];
      for (const benchmarkCase of benchmarkCases) {
        setProgressLabel(`Running ${benchmarkCase.language.toUpperCase()} fixture`);
        const generation = await client.generate(benchmarkCase.prompt, benchmarkCase.schema);
        measured.push(evaluateBenchmarkResult(benchmarkCase, generation));
        setResults([...measured]);
      }
      setState("ready");
      setProgressLabel("Benchmark complete");
    } catch {
      setState("error");
      setProgressLabel("Benchmark stopped before completion");
    }
  }

  function cancel() {
    clientRef.current?.cancel();
    setProgressLabel("Cancelling local operation");
  }

  async function clearCache() {
    const client = clientRef.current ?? createBrowserAIClient();
    clientRef.current = client;
    setProgressLabel("Clearing model cache");
    try {
      await client.clearCache(selectedModel);
      setState("idle");
      setProgress(0);
      setResults([]);
      setProgressLabel("Local model cache cleared");
    } catch {
      setState("error");
      setProgressLabel("Model cache could not be cleared");
    }
  }

  return (
    <section aria-labelledby="browser-ai-title" className="browser-ai-lab" id="browser-ai">
      <div className="section-heading">
        <div><span className="section-index">02</span><h2 id="browser-ai-title">Browser AI laboratory</h2></div>
        <p>An explicit, local-only runtime spike. Models are never downloaded until you approve their size and license.</p>
      </div>

      <div className="browser-ai-grid">
        <div className="browser-ai-panel">
          <div className="capability-row" aria-label="Browser AI capabilities">
            <span className={supported ? "capability-ok" : "capability-missing"}>WebGPU {capabilities?.webGpu ? "ready" : "missing"}</span>
            <span>WASM {capabilities?.webAssembly ? "ready" : "missing"}</span>
            <span>{capabilities?.deviceMemoryGb ? `${String(capabilities.deviceMemoryGb)} GB reported RAM` : "RAM unknown"}</span>
          </div>

          <label className="model-label" htmlFor="browser-model">Experimental model</label>
          <select
            disabled={state === "loading" || state === "benchmarking"}
            id="browser-model"
            onChange={(event) => {
              setSelectedId(event.target.value);
              setConsented(false);
            }}
            value={selectedModel.id}
          >
            {browserAIModels.map((model) => <option key={model.id} value={model.id}>{model.name} · {model.runtime}</option>)}
          </select>

          <dl className="model-facts">
            <div><dt>Download</dt><dd>{formatBytes(selectedModel.downloadBytes)}</dd></div>
            <div><dt>Recommended RAM</dt><dd>{selectedModel.recommendedMemoryGb} GB</dd></div>
            <div><dt>License</dt><dd>{selectedModel.license}</dd></div>
            <div><dt>Output</dt><dd>{selectedModel.structuredOutput}</dd></div>
          </dl>

          <label className="download-consent">
            <input checked={consented} onChange={(event) => { setConsented(event.target.checked); }} type="checkbox" />
            <span>I approve this one-time model download and local browser storage.</span>
          </label>

          <div className="browser-ai-actions">
            <Button disabled={!supported || !consented || state === "loading" || state === "benchmarking"} onClick={() => void loadModel()}>
              Load locally
            </Button>
            <Button disabled={state !== "ready"} onClick={() => void runBenchmark()} variant="secondary">Run bilingual benchmark</Button>
            {(state === "loading" || state === "benchmarking") && <Button onClick={cancel} variant="ghost">Cancel</Button>}
            <Button disabled={state === "loading" || state === "benchmarking"} onClick={() => void clearCache()} variant="ghost">Clear cache</Button>
          </div>

          <div aria-live="polite" className="model-progress">
            <div><span style={{ width: `${String(Math.round(progress * 100))}%` }} /></div>
            <p>{progressLabel}</p>
          </div>
        </div>

        <div className="benchmark-panel">
          <span className="card-kicker">Deterministic evaluation</span>
          <h3>Same fixtures, visible trade-offs</h3>
          <p>The model runs off the main thread. Only timing and pass/fail metadata are retained by this screen.</p>
          {results.length === 0 ? (
            <div className="benchmark-empty">Load a model to measure English and Spanish JSON adherence.</div>
          ) : (
            <div className="benchmark-results">
              {results.map((result) => (
                <article key={result.caseId}>
                  <strong>{result.language.toUpperCase()}</strong>
                  <span>{result.schemaValid ? "Schema passed" : "Schema failed"}</span>
                  <small>{Math.round(result.metrics.totalTimeMs)} ms · {result.metrics.tokensPerSecond?.toFixed(1) ?? "—"} tok/s</small>
                </article>
              ))}
            </div>
          )}
          <p className="privacy-note">No cloud fallback. Cancelling interrupts inference; changing runtime requires a fresh explicit load.</p>
        </div>
      </div>
    </section>
  );
}
