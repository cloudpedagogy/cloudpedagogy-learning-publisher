import base64
import json
import re
from pathlib import Path


WEBR_EMBED_MAX_FILE_BYTES = 2 * 1024 * 1024       # 2 MiB per file
WEBR_EMBED_MAX_PAGE_BYTES = 5 * 1024 * 1024       # 5 MiB total per page


WEBR_DATA_RESOURCE_RE = re.compile(
    r"""(?P<quote>["'])(?P<path>resources/data/[^"'\r\n]+)(?P=quote)""",
    re.IGNORECASE,
)


def extract_webr_data_resources(code: str) -> list[str]:
    """
    Return unique literal course-data paths referenced by a WebR code block.

    Only quoted paths rooted at ``resources/data/`` are considered. This keeps
    automatic staging deliberately narrow and avoids rewriting arbitrary URLs,
    local paths, or dynamically constructed R strings.
    """
    found = []
    seen = set()

    for match in WEBR_DATA_RESOURCE_RE.finditer(code):
        raw_path = match.group("path").strip().replace("\\", "/")
        path_obj = Path(raw_path)

        # Reject paths that could escape the intended course data area.
        if (
            path_obj.is_absolute()
            or ".." in path_obj.parts
            or not raw_path.lower().startswith("resources/data/")
        ):
            continue

        if raw_path not in seen:
            seen.add(raw_path)
            found.append(raw_path)

    return found

def validate_webr_data_resource(
    resource_path: str,
    course_source_dir: Path,
) -> Path:
    """
    Resolve and validate a WebR course-data resource safely.

    The path must remain inside ``<course>/resources/data/`` and refer to an
    existing file. Symlink/path traversal outside that directory is rejected.
    """
    normalized = resource_path.strip().replace("\\", "/")
    relative_path = Path(normalized)

    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(
            f"WebR data resource must be a safe course-relative path: {resource_path}"
        )

    if len(relative_path.parts) < 3 or tuple(
        part.lower() for part in relative_path.parts[:2]
    ) != ("resources", "data"):
        raise ValueError(
            "Automatic WebR data staging is restricted to resources/data/: "
            f"{resource_path}"
        )

    course_root = course_source_dir.resolve()
    data_root = (course_root / "resources" / "data").resolve()
    source_path = (course_root / relative_path).resolve()

    try:
        source_path.relative_to(data_root)
    except ValueError as exc:
        raise ValueError(
            "WebR data resource must remain inside the course resources/data folder: "
            f"{resource_path}"
        ) from exc

    if not source_path.is_file():
        raise FileNotFoundError(
            f"WebR data resource not found: {source_path}"
        )

    return source_path

def build_webr_data_bootstrap_script(
    resource_paths: list[str],
    qmd_path: Path,
    course_dir: Path,
    course_source_dir: Path,
) -> str:
    """
    Embed small course data files into the generated page and stage them into
    WebR's virtual filesystem after WebR initializes.

    Why embed instead of fetch:
    - no ``download.file()``;
    - no browser ``fetch()``;
    - no CORS or ``file://`` restrictions;
    - no dependency on site-relative URLs or hosting layout;
    - works for local/offline rendered output as well as HTTP-hosted output;
    - learner R remains unchanged, e.g.
      ``read.csv("resources/data/example.csv")``.

    Safety and scope:
    - only literal paths already restricted to ``resources/data/...`` reach
      this function;
    - each path is validated against the course source directory;
    - per-file and per-page size limits prevent accidental HTML bloat;
    - arbitrary binary files are supported by Base64 encoding;
    - quarto-webr extension files are never modified;
    - ordinary R and WebR blocks without course-data dependencies are unchanged.

    The runtime bridge uses WebR's public JavaScript API:
    ``evalRString()``, ``FS.lookupPath()``, ``FS.mkdir()`` and
    ``FS.writeFile()``.

    ``qmd_path`` and ``course_dir`` remain in the signature for compatibility
    with the import pipeline, although embedded data no longer needs URL
    rewriting.
    """
    if not resource_paths:
        return ""

    resources = []
    total_bytes = 0

    for resource_path in resource_paths:
        source_path = validate_webr_data_resource(
            resource_path,
            course_source_dir,
        )

        size = source_path.stat().st_size
        if size > WEBR_EMBED_MAX_FILE_BYTES:
            raise ValueError(
                "WebR course data file is too large for automatic inline "
                f"embedding ({size:,} bytes; limit "
                f"{WEBR_EMBED_MAX_FILE_BYTES:,}): {resource_path}"
            )

        total_bytes += size
        if total_bytes > WEBR_EMBED_MAX_PAGE_BYTES:
            raise ValueError(
                "Total WebR course data referenced by this page is too large "
                f"for automatic inline embedding ({total_bytes:,} bytes; limit "
                f"{WEBR_EMBED_MAX_PAGE_BYTES:,})."
            )

        raw_bytes = source_path.read_bytes()
        encoded = base64.b64encode(raw_bytes).decode("ascii")

        resources.append(
            {
                "destination": resource_path.replace("\\", "/"),
                "base64": encoded,
                "size": size,
            }
        )

    payload = json.dumps(
        resources,
        ensure_ascii=True,
        separators=(",", ":"),
    )

    # qmd_path/course_dir are intentionally unused in this implementation.
    # Keeping them avoids widening the change across the import pipeline.
    _ = qmd_path, course_dir

    return f"""<script>
(() => {{
  "use strict";

  const resources = {payload};
  const timeoutMs = 30000;
  const pollMs = 25;

  async function waitForGlobal(name, timeout = timeoutMs) {{
    const started = performance.now();

    while (typeof globalThis[name] === "undefined") {{
      if (performance.now() - started > timeout) {{
        throw new Error(
          `Timed out waiting for quarto-webr global '${{name}}'.`
        );
      }}

      await new Promise(resolve => setTimeout(resolve, pollMs));
    }}

    return globalThis[name];
  }}

  function normaliseVfsPath(path) {{
    if (typeof path !== "string" || !path.trim()) {{
      throw new Error("WebR returned an empty working directory.");
    }}

    let value = path.replace(/\\\\/g, "/").replace(/\\/+/g, "/");

    if (!value.startsWith("/")) {{
      value = "/" + value;
    }}

    if (value.length > 1) {{
      value = value.replace(/\\/+$/, "");
    }}

    return value;
  }}

  function joinVfsPath(base, relative) {{
    const cleanBase = normaliseVfsPath(base);
    const cleanRelative = relative
      .replace(/\\\\/g, "/")
      .replace(/^\\/+/, "");

    return cleanBase === "/"
      ? `/${{cleanRelative}}`
      : `${{cleanBase}}/${{cleanRelative}}`;
  }}

  async function ensureAbsoluteDirectory(fs, absolutePath) {{
    const normalised = normaliseVfsPath(absolutePath);

    if (normalised === "/") {{
      return;
    }}

    const parts = normalised.split("/").filter(Boolean);
    let current = "";

    for (const part of parts) {{
      current += `/${{part}}`;

      try {{
        await fs.lookupPath(current);
      }} catch (_) {{
        await fs.mkdir(current);
      }}
    }}
  }}

  function decodeBase64(base64Text, expectedSize) {{
    const binary = atob(base64Text);
    const bytes = new Uint8Array(binary.length);

    for (let index = 0; index < binary.length; index += 1) {{
      bytes[index] = binary.charCodeAt(index);
    }}

    if (bytes.byteLength !== expectedSize) {{
      throw new Error(
        `Embedded WebR data size mismatch: expected ${{expectedSize}} bytes, ` +
        `decoded ${{bytes.byteLength}} bytes.`
      );
    }}

    return bytes;
  }}

  async function stageCourseData() {{
    // quarto-webr currently exposes qwebrInstance as its page-level
    // initialization promise and mainWebR as the persistent WebR instance.
    // These are feature-detected so a future integration change fails only
    // automatic data staging rather than ordinary WebR.
    const qwebrInstance = await waitForGlobal("qwebrInstance");
    await qwebrInstance;

    const mainWebR = await waitForGlobal("mainWebR");

    if (
      !mainWebR ||
      typeof mainWebR.evalRString !== "function" ||
      !mainWebR.FS ||
      typeof mainWebR.FS.lookupPath !== "function" ||
      typeof mainWebR.FS.mkdir !== "function" ||
      typeof mainWebR.FS.writeFile !== "function"
    ) {{
      throw new Error(
        "The active quarto-webr/WebR integration does not expose the expected " +
        "WebR API. Ordinary WebR can continue, but automatic course-data " +
        "staging is unavailable."
      );
    }}

    // R resolves relative paths against getwd(). Stage the embedded file under
    // that exact directory so the learner's original relative path resolves.
    const rWorkingDirectory = normaliseVfsPath(
      await mainWebR.evalRString("getwd()")
    );

    for (const resource of resources) {{
      const destination = joinVfsPath(
        rWorkingDirectory,
        resource.destination
      );

      const lastSlash = destination.lastIndexOf("/");
      const parent = lastSlash > 0
        ? destination.slice(0, lastSlash)
        : "/";

      await ensureAbsoluteDirectory(mainWebR.FS, parent);

      // Do not decode/write the same resource twice in one WebR instance.
      try {{
        await mainWebR.FS.lookupPath(destination);
        continue;
      }} catch (_) {{
        // Not present yet.
      }}

      const bytes = decodeBase64(resource.base64, resource.size);
      await mainWebR.FS.writeFile(destination, bytes);

      // Verify that the expected VFS node now exists.
      await mainWebR.FS.lookupPath(destination);
    }}

    return true;
  }}

  // Chain data-aware blocks on the same page rather than racing them.
  const previous = globalThis.qwebrCourseDataReady || Promise.resolve();

  globalThis.qwebrCourseDataReady = previous
    .then(stageCourseData)
    .catch(error => {{
      console.error(
        "[Learning Publisher] WebR embedded course-data staging failed:",
        error
      );
      throw error;
    }});

  // Best-effort readiness guard. If the current quarto-webr build exposes its
  // compute entry point globally, make execution wait for staging. If a future
  // version changes that symbol, staging still starts immediately after WebR
  // initialization and the failure is reported in the console without
  // modifying the third-party extension.
  (async () => {{
    const originalCompute = await waitForGlobal("qwebrComputeEngine");

    if (
      typeof originalCompute !== "function" ||
      originalCompute.__learningPublisherDataGuard === true
    ) {{
      return;
    }}

    const guardedCompute = async function(...args) {{
      if (globalThis.qwebrCourseDataReady) {{
        await globalThis.qwebrCourseDataReady;
      }}

      return originalCompute.apply(this, args);
    }};

    Object.defineProperty(
      guardedCompute,
      "__learningPublisherDataGuard",
      {{
        value: true,
        enumerable: false,
        configurable: false,
        writable: false,
      }}
    );

    globalThis.qwebrComputeEngine = guardedCompute;
  }})().catch(error => {{
    console.error(
      "[Learning Publisher] Unable to install WebR data readiness guard:",
      error
    );
  }});
}})();
</script>"""
