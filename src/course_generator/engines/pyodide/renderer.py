"""Minimal browser-side Pyodide renderer for Learning Publisher."""

import html
import json


PYODIDE_VERSION = "0.29.2"
PYODIDE_BASE_URL = (
    f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"
)
PYODIDE_SCRIPT_URL = PYODIDE_BASE_URL + "pyodide.js"


def render_pyodide_widget(
    code: str,
    widget_id: str,
    data_files: list[dict] | None = None,
) -> str:
    """
    Render an editable Python exercise powered by Pyodide in the browser.

    Stage 4C scope:
    - editable Python textarea;
    - Run button;
    - captured stdout/stderr;
    - one shared Pyodide runtime per page;
    - no third-party package loading yet;
    - no course-data staging yet.
    """
    safe_widget_id = html.escape(widget_id, quote=True)
    safe_code = html.escape(code, quote=False)
    js_widget_id = json.dumps(widget_id)
    js_script_url = json.dumps(PYODIDE_SCRIPT_URL)
    js_base_url = json.dumps(PYODIDE_BASE_URL)
    js_data_files = json.dumps(data_files or [])

    return f"""```{{=html}}
<div class="learning-publisher-pyodide" id="{safe_widget_id}">
  <label for="{safe_widget_id}-code"><strong>Python code</strong></label>
  <textarea id="{safe_widget_id}-code"
            class="learning-publisher-pyodide-code"
            rows="8"
            spellcheck="false">{safe_code}</textarea>
  <p class="learning-publisher-pyodide-actions">
    <button type="button"
            class="learning-publisher-pyodide-run">Run Python</button>
    <span class="learning-publisher-pyodide-status"
          role="status"
          aria-live="polite"></span>
  </p>
  <div class="learning-publisher-pyodide-output-group">
    <strong>Output</strong>
    <pre class="learning-publisher-pyodide-output"
         tabindex="0"
         aria-live="polite"></pre>
    <div class="learning-publisher-pyodide-figures"
         aria-live="polite"></div>
  </div>
</div>

<script>
(() => {{
  "use strict";

  const widgetId = {js_widget_id};
  const scriptUrl = {js_script_url};
  const indexURL = {js_base_url};
  const dataFiles = {js_data_files};

  function withTimeout(promise, timeoutMs, message) {{
    return Promise.race([
      promise,
      new Promise((_, reject) => {{
        window.setTimeout(
          () => reject(new Error(message)),
          timeoutMs
        );
      }})
    ]);
  }}

  function loadPyodideScriptOnce() {{
    if (typeof globalThis.loadPyodide === "function") {{
      return Promise.resolve();
    }}

    if (globalThis.learningPublisherPyodideScriptPromise) {{
      return globalThis.learningPublisherPyodideScriptPromise;
    }}

    globalThis.learningPublisherPyodideScriptPromise = new Promise(
      (resolve, reject) => {{
        const existing = document.querySelector(
          'script[data-learning-publisher-pyodide="true"]'
        );

        if (existing) {{
          existing.addEventListener("load", resolve, {{ once: true }});
          existing.addEventListener(
            "error",
            () => reject(new Error("Unable to load Pyodide runtime.")),
            {{ once: true }}
          );
          return;
        }}

        const script = document.createElement("script");
        script.src = scriptUrl;
        script.async = true;
        script.dataset.learningPublisherPyodide = "true";
        script.addEventListener("load", resolve, {{ once: true }});
        script.addEventListener(
          "error",
          () => reject(new Error("Unable to load Pyodide runtime.")),
          {{ once: true }}
        );
        document.head.appendChild(script);
      }}
    );

    return globalThis.learningPublisherPyodideScriptPromise;
  }}

  async function getPyodide() {{
    if (!globalThis.learningPublisherPyodidePromise) {{
      globalThis.learningPublisherPyodidePromise = (async () => {{
        await withTimeout(
          loadPyodideScriptOnce(),
          20000,
          "Timed out while loading the Pyodide JavaScript runtime."
        );

        if (typeof globalThis.loadPyodide !== "function") {{
          throw new Error(
            "Pyodide script loaded but loadPyodide() is unavailable."
          );
        }}

        return withTimeout(
          globalThis.loadPyodide({{ indexURL }}),
          60000,
          "Timed out while initialising Pyodide. Check the browser console and network connection."
        );
      }})();
    }}

    return globalThis.learningPublisherPyodidePromise;
  }}

  function base64ToBytes(base64Text) {{
    const binary = atob(base64Text);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {{
      bytes[i] = binary.charCodeAt(i);
    }}
    return bytes;
  }}

  function stageDataFiles(pyodide) {{
    if (!Array.isArray(dataFiles) || dataFiles.length === 0) {{
      return;
    }}

    const cwd = pyodide.FS.cwd();

    try {{
      pyodide.FS.mkdirTree(cwd + "/data");
    }} catch (_) {{
      // Directory may already exist.
    }}

    dataFiles.forEach((item) => {{
      const target = String(item.target || "");
      const payload = String(item.base64 || "");

      if (!target.startsWith("data/") || !payload) {{
        throw new Error("Invalid embedded Python data resource.");
      }}

      const absoluteTarget = cwd + "/" + target;
      const bytes = base64ToBytes(payload);
      pyodide.FS.writeFile(absoluteTarget, bytes);
    }});
  }}

  async function runCode(code) {{
    const pyodide = await getPyodide();

    // Pyodide does not preload most third-party packages. Inspect import
    // statements in the learner code and load supported Pyodide packages
    // (for example matplotlib, numpy or pandas) before execution.
    await withTimeout(
      pyodide.loadPackagesFromImports(code),
      120000,
      "Timed out while loading Python packages."
    );

    stageDataFiles(pyodide);

    // Pass learner code through Pyodide's globals rather than interpolating
    // it into Python source. This keeps quotes/backslashes/newlines safe.
    pyodide.globals.set("__lp_user_code", code);

    try {{
      const resultJson = await pyodide.runPythonAsync(`
import base64
import contextlib
import io
import json
import traceback

_lp_stdout = io.StringIO()
_lp_stderr = io.StringIO()
_lp_figures = []

try:
    # If matplotlib is available, force a non-interactive backend before
    # learner code imports pyplot. This prevents the default browser figure
    # manager / toolbar UI from appearing.
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
    except Exception:
        pass

    # Learner code commonly uses plt.show(). Under the deliberately
    # non-interactive Agg backend, show() would emit a harmless warning.
    # Temporarily replace it with a no-op because Learning Publisher captures
    # the resulting figures itself immediately after execution.
    _lp_original_show = None
    try:
        import matplotlib.pyplot as plt
        _lp_original_show = plt.show
        plt.show = lambda *args, **kwargs: None
    except Exception:
        pass

    try:
        with contextlib.redirect_stdout(_lp_stdout), contextlib.redirect_stderr(_lp_stderr):
            exec(compile(__lp_user_code, "<learning-publisher>", "exec"), {{}})
    finally:
        if _lp_original_show is not None:
            try:
                plt.show = _lp_original_show
            except Exception:
                pass

    # Capture any matplotlib figures created by learner code as PNG images.
    try:
        import matplotlib.pyplot as plt

        for _lp_number in plt.get_fignums():
            _lp_figure = plt.figure(_lp_number)
            _lp_buffer = io.BytesIO()
            _lp_figure.savefig(
                _lp_buffer,
                format="png",
                bbox_inches="tight",
                dpi=144,
            )
            _lp_figures.append(
                base64.b64encode(_lp_buffer.getvalue()).decode("ascii")
            )
            _lp_buffer.close()

        plt.close("all")
    except Exception:
        # Figure capture should never make otherwise-valid Python fail.
        pass

except Exception:
    traceback.print_exc(file=_lp_stderr)

json.dumps({{
    "stdout": _lp_stdout.getvalue(),
    "stderr": _lp_stderr.getvalue(),
    "figures": _lp_figures,
}})
      `);

      return JSON.parse(resultJson);
    }} finally {{
      try {{
        pyodide.globals.delete("__lp_user_code");
      }} catch (_) {{
        // Cleanup is best-effort only.
      }}
    }}
  }}

  function initialiseWidget() {{
    const root = document.getElementById(widgetId);
    if (!root || root.dataset.pyodideInitialised === "true") {{
      return;
    }}

    root.dataset.pyodideInitialised = "true";

    const textarea = root.querySelector(
      ".learning-publisher-pyodide-code"
    );
    const button = root.querySelector(
      ".learning-publisher-pyodide-run"
    );
    const status = root.querySelector(
      ".learning-publisher-pyodide-status"
    );
    const output = root.querySelector(
      ".learning-publisher-pyodide-output"
    );
    const figures = root.querySelector(
      ".learning-publisher-pyodide-figures"
    );

    button.addEventListener("click", async () => {{
      button.disabled = true;
      status.textContent = "Loading Python and packages…";
      button.setAttribute("aria-busy", "true");
      output.textContent = "";
      figures.replaceChildren();

      try {{
        const result = await runCode(textarea.value);
        const stdout = result.stdout || "";
        const stderr = result.stderr || "";
        const figureData = Array.isArray(result.figures)
          ? result.figures
          : [];

        figureData.forEach((base64Png, index) => {{
          const figure = document.createElement("figure");
          figure.className = "learning-publisher-pyodide-figure";

          const image = document.createElement("img");
          image.src = `data:image/png;base64,${{base64Png}}`;
          image.alt = `Python-generated figure ${{index + 1}}`;
          image.loading = "lazy";

          figure.appendChild(image);
          figures.appendChild(figure);
        }});

        if (stderr) {{
          output.textContent = stdout
            ? stdout + (stdout.endsWith("\\n") ? "" : "\\n") + stderr
            : stderr;
          status.textContent = "Finished with an error.";
        }} else {{
          output.textContent = stdout || (
            figureData.length ? "" : "(No text output)"
          );
          status.textContent = "Finished.";
        }}
      }} catch (error) {{
        console.error(
          "[Learning Publisher] Pyodide execution failed:",
          error
        );
        output.textContent =
          error && error.message
            ? error.message
            : String(error);
        status.textContent = "Python could not run.";
      }} finally {{
        button.disabled = false;
        button.removeAttribute("aria-busy");
      }}
    }});
  }}

  if (document.readyState === "loading") {{
    document.addEventListener(
      "DOMContentLoaded",
      initialiseWidget,
      {{ once: true }}
    );
  }} else {{
    initialiseWidget();
  }}
}})();
</script>

<style>
.learning-publisher-pyodide {{
  border: 1px solid #d9d9d9;
  border-radius: .4rem;
  margin: 1rem 0;
  padding: 1rem;
}}
.learning-publisher-pyodide-code {{
  box-sizing: border-box;
  display: block;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
  margin-top: .4rem;
  min-height: 10rem;
  width: 100%;
}}
.learning-publisher-pyodide-actions {{
  align-items: center;
  display: flex;
  gap: .75rem;
  margin: .75rem 0;
}}
.learning-publisher-pyodide-output {{
  background: #f6f8fa;
  border: 1px solid #d9d9d9;
  min-height: 3rem;
  overflow-x: auto;
  padding: .75rem;
  white-space: pre-wrap;
}}
.learning-publisher-pyodide-output:empty {{
  display: none;
}}
.learning-publisher-pyodide-figures {{
  margin-top: .75rem;
}}
.learning-publisher-pyodide-figure {{
  margin: 0;
}}
.learning-publisher-pyodide-figure img {{
  display: block;
  height: auto;
  max-width: 100%;
}}
</style>
``` 
""".strip()
