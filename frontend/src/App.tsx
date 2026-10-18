import { useState } from "react";
import GraphView from "./GraphView";
import "./App.css";

type ImpactResult = {
  changed_function: string;
  affected_components: string[];
  related_tests: string[];
  message: string;
};

type UploadResult = {
  project_id: string;
  functions_stored: number;
  relationships_stored: number;
  files_analysed: number;
  functions_found: string[];
  calls_found: { caller: string; callee: string }[];
  message: string;
};

function App() {
  const [functionName, setFunctionName] = useState("");
  const [result, setResult] = useState<ImpactResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  const [projectId, setProjectId] = useState("tracewise");

  async function uploadProject() {
    if (!selectedFile) {
      setUploadError("Please select a ZIP file first.");
      return;
    }

    setUploading(true);
    setUploadError("");
    setUploadResult(null);
    setResult(null);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch("http://localhost:8000/projects/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Project upload failed.");
      }

      setUploadResult(data);
      setProjectId(data.project_id);
      setFunctionName(data.functions_found[0] ?? "");
    } catch (err) {
      setUploadError(
        err instanceof Error
          ? err.message
          : "Unable to connect to the TraceWise API.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function analyzeImpact() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("http://localhost:8000/impact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          function_name: functionName,
          project_id: projectId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Impact analysis failed.");
      }

      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to the TraceWise API.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">T</div>
          <span>TraceWise</span>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <button className="nav-item active">
          <span>⌘</span> Impact Analysis
        </button>

        <div className="sidebar-bottom">
          <div className="status-dot" />
          <span>Graph database connected</span>
        </div>
      </aside>

      <section className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> Impact Analysis
          </div>
          <div className="database-badge">
            <span className="status-dot" />
            FalkorDB
          </div>
        </header>

        <div className="page-content">
          <div className="eyebrow">DEVELOPER TOOLKIT</div>

          <h1>
            Understand the impact
            <br />
            <span>before you change code.</span>
          </h1>

          <p className="intro">
            Trace dependencies across your codebase and discover which
            components and tests may be affected by a change.
          </p>

          <section className="analysis-card">
            <div className="card-heading">
              <div>
                <div className="section-kicker">NEW PROJECT</div>
                <h2>Upload your codebase</h2>
              </div>
              <div className="card-icon">↑</div>
            </div>

            <p className="intro">
              Upload a ZIP containing JavaScript or TypeScript source files.
            </p>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void uploadProject();
              }}
            >
              <label htmlFor="project-zip">Project ZIP file</label>

              <div className="input-row">
                <div className="input-wrap">
                  <input
                    id="project-zip"
                    type="file"
                    accept=".zip,application/zip"
                    onChange={(event) => {
                      setSelectedFile(event.target.files?.[0] ?? null);
                      setUploadError("");
                      setUploadResult(null);
                    }}
                  />
                </div>

                <button type="submit" disabled={uploading || !selectedFile}>
                  {uploading ? "Uploading..." : "Upload project"}
                  {!uploading && <span>↑</span>}
                </button>
              </div>
            </form>

            <div className="helper-text">
              <span>ⓘ</span> Maximum ZIP size: 20 MB. Supported files: JS, JSX,
              TS and TSX.
            </div>

            {uploadError && (
              <div className="error-banner">
                <strong>Upload failed</strong>
                <p>{uploadError}</p>
              </div>
            )}

            {uploadResult && (
              <div className="upload-summary">
                <div className="section-kicker">PROJECT ANALYSED</div>
                <h3>Your project is ready!</h3>

                <div className="result-grid">
                  <article className="result-card">
                    <div className="count">{uploadResult.files_analysed}</div>
                    <h3>Files analysed</h3>
                  </article>

                  <article className="result-card">
                    <div className="count">{uploadResult.functions_stored}</div>
                    <h3>Functions discovered</h3>
                  </article>

                  <article className="result-card">
                    <div className="count">
                      {uploadResult.relationships_stored}
                    </div>
                    <h3>Relationships created</h3>
                  </article>
                </div>

                <div className="graph-section">
                  <div className="section-kicker">CODE RELATIONSHIPS</div>
                  <h3>Function dependency graph</h3>
                  <p className="helper-text">
                    Explore how functions in your project connect to one
                    another.
                  </p>

                  <GraphView projectId={projectId} />
                </div>
              </div>
            )}
          </section>

          <section className="analysis-card">
            <div className="card-heading">
              <div>
                <div className="section-kicker">IMPACT ANALYSIS</div>
                <h2>Analyze a function</h2>
              </div>
              <div className="card-icon">↗</div>
            </div>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void analyzeImpact();
              }}
            >
              <label htmlFor="impact-function-name">
                Select function to analyse
              </label>

              <div className="input-row">
                <div className="function-select-wrapper">
                  <span className="function-select-icon" aria-hidden="true">
                    ƒ
                  </span>

                  <select
                    id="impact-function-name"
                    className="function-select"
                    value={functionName}
                    onChange={(event) => setFunctionName(event.target.value)}
                    disabled={
                      !uploadResult || uploadResult.functions_found.length === 0
                    }
                    required
                  >
                    {uploadResult?.functions_found.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>

                  <span className="function-select-arrow" aria-hidden="true">
                    ↓
                  </span>
                </div>

                <button
                  type="submit"
                  disabled={
                    loading ||
                    !uploadResult ||
                    uploadResult.functions_found.length === 0
                  }
                >
                  {loading ? "Analyzing..." : "Analyze impact"}
                  {!loading && <span>→</span>}
                </button>
              </div>
            </form>

            <div className="helper-text">
              <span>ⓘ</span> Analysis is powered by graph relationships in
              FalkorDB.
            </div>
          </section>

          {error && (
            <div className="error-banner">
              <strong>Analysis failed</strong>
              <p>{error}</p>
              <span>
                Check that the TraceWise backend is running on port 8000.
              </span>
            </div>
          )}

          {result && (
            <section className="results-section">
              <div className="results-heading">
                <div>
                  <div className="section-kicker">ANALYSIS RESULTS</div>
                  <h2>Impact overview</h2>
                </div>
                <span className="success-badge">
                  <span className="status-dot" /> Analysis complete
                </span>
              </div>

              <div className="summary-card">
                <div className="summary-icon">ƒ</div>
                <div>
                  <div className="muted-label">FUNCTION ANALYZED</div>
                  <h3>{result.changed_function}</h3>
                </div>
                <span className="function-tag">Function</span>
              </div>

              <div className="result-grid">
                <article className="result-card">
                  <div className="result-card-top">
                    <span className="result-icon affected-icon">◇</span>
                    <span className="count">
                      {result.affected_components.length}
                    </span>
                  </div>
                  <h3>Affected components</h3>
                  <p>Dependencies that may be impacted by this change.</p>

                  {result.affected_components.length > 0 ? (
                    <ul className="result-list">
                      {result.affected_components.map((name) => (
                        <li key={name}>
                          <span className="list-symbol">↳</span>
                          <code>{name}</code>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="empty-state">No affected components found.</p>
                  )}
                </article>

                <article className="result-card">
                  <div className="result-card-top">
                    <span className="result-icon test-icon">✓</span>
                    <span className="count">{result.related_tests.length}</span>
                  </div>
                  <h3>Related tests</h3>
                  <p>Tests directly linked to the function being analyzed.</p>

                  {result.related_tests.length > 0 ? (
                    <ul className="result-list">
                      {result.related_tests.map((name) => (
                        <li key={name}>
                          <span className="list-symbol">✓</span>
                          <code>{name}</code>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="empty-state">No related tests found.</p>
                  )}
                </article>
              </div>

              <div className="results-note">
                <span>✳</span>
                <p>
                  <strong>Before you commit:</strong> Review the affected
                  components and consider running the related tests before
                  merging your change.
                </p>
              </div>
            </section>
          )}

          {!result && !error && !uploadResult && (
            <div className="empty-dashboard">
              <div className="empty-illustration">⌘</div>
              <h3>Your next change, mapped.</h3>
              <p>
                Upload a project to discover its functions, then analyse their
                dependencies.
              </p>
            </div>
          )}

          <footer>
            <span>TRACEWISE</span>
            <span>Graph-powered code impact analysis</span>
          </footer>
        </div>
      </section>
    </main>
  );
}

export default App;
