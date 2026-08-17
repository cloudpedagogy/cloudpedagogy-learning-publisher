"""Lazy missing-package support for browser-side WebR activities."""

import re


_PACKAGE_USE_RE = re.compile(
    r"""
    (?:
        \b(?:library|require|requireNamespace)\s*\(
        |
        \b[A-Za-z][A-Za-z0-9._]*\s*:::{0,1}
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def webr_code_may_need_packages(code: str) -> bool:
    """
    Return True when R code appears to reference a package.

    This is only a trigger. WebR itself determines whether a referenced
    package is actually missing when the learner executes the activity.
    """
    return bool(_PACKAGE_USE_RE.search(code or ""))


def build_webr_lazy_package_bootstrap_script() -> str:
    """
    Enable WebR's missing-package handler after WebR initialises.

    Enabling the handler does not install packages during page load.
    Missing packages are installed later if learner-executed R code
    actually requires them.
    """
    return """```{=html}
<script>
(() => {
  if (globalThis.__learningPublisherWebRPackageBootstrap) {
    return;
  }

  globalThis.__learningPublisherWebRPackageBootstrap = true;

  async function waitForGlobal(name, timeoutMs = 30000) {
    const started = Date.now();

    while (Date.now() - started < timeoutMs) {
      if (
        globalThis[name] !== undefined &&
        globalThis[name] !== null
      ) {
        return globalThis[name];
      }

      await new Promise(resolve => setTimeout(resolve, 50));
    }

    throw new Error(`Timed out waiting for ${name}.`);
  }

  (async () => {
    const qwebrInstance = await waitForGlobal("qwebrInstance");
    await qwebrInstance;

    const mainWebR = await waitForGlobal("mainWebR");

    if (
      !mainWebR ||
      typeof mainWebR.evalRVoid !== "function"
    ) {
      throw new Error(
        "The active quarto-webr integration does not expose " +
        "mainWebR.evalRVoid()."
      );
    }

    await mainWebR.evalRVoid(
      "webr::global_prompt_install()"
    );
  })().catch(error => {
    console.error(
      "[Learning Publisher] Unable to enable lazy WebR " +
      "package installation:",
      error
    );
  });
})();
</script>
```"""
