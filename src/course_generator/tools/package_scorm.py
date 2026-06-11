#!/usr/bin/env python3
"""
Package a rendered Quarto HTML site as a basic SCORM 1.2 package.

This script works on a COPY of your rendered web output.
It does not modify the original site folder.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import zipfile
from pathlib import Path


SCORM_API_WRAPPER_JS = r"""
(function () {
  function findAPI(win) {
    var attempts = 0;

    while ((win.API == null) && (win.parent != null) && (win.parent !== win)) {
      attempts++;
      if (attempts > 500) return null;
      win = win.parent;
    }

    return win.API;
  }

  function getAPI() {
    var api = findAPI(window);

    if ((api == null) && (window.opener != null)) {
      api = findAPI(window.opener);
    }

    return api;
  }

  window.scormAPI = null;
  window.scormInitialised = false;

  window.scormInit = function () {
    window.scormAPI = getAPI();

    if (!window.scormAPI) {
      console.warn("SCORM API not found. This is expected outside Moodle SCORM.");
      return;
    }

    window.scormInitialised = window.scormAPI.LMSInitialize("") === "true";

    if (window.scormInitialised) {
      var currentStatus = window.scormAPI.LMSGetValue("cmi.core.lesson_status");

      if (currentStatus !== "completed" && currentStatus !== "passed") {
        window.scormAPI.LMSSetValue("cmi.core.lesson_status", "incomplete");
      }

      window.scormAPI.LMSCommit("");
    }
  };

  window.scormSetComplete = function () {
    if (window.scormAPI && window.scormInitialised) {
      window.scormAPI.LMSSetValue("cmi.core.lesson_status", "completed");
      window.scormAPI.LMSSetValue("cmi.core.score.raw", "100");
      window.scormAPI.LMSCommit("");
    }
  };

  window.scormFinish = function () {
    if (window.scormAPI && window.scormInitialised) {
      window.scormAPI.LMSCommit("");
      window.scormAPI.LMSFinish("");
      window.scormInitialised = false;
    }
  };

  window.addEventListener("load", window.scormInit);
  window.addEventListener("beforeunload", window.scormFinish);
})();
"""


SCORM_TRACKING_JS = r"""
(function () {
  function addCompletionButton() {
    if (document.getElementById("scorm-completion-button")) return;

    var button = document.createElement("button");
    button.id = "scorm-completion-button";
    button.innerText = "Mark complete";
    button.setAttribute("type", "button");
    button.style.position = "fixed";
    button.style.right = "1rem";
    button.style.bottom = "1rem";
    button.style.zIndex = "9999";
    button.style.padding = "0.75rem 1rem";
    button.style.borderRadius = "0.5rem";
    button.style.border = "1px solid #333";
    button.style.background = "#fff";
    button.style.color = "#111";
    button.style.cursor = "pointer";
    button.style.boxShadow = "0 2px 8px rgba(0,0,0,0.2)";
    button.style.fontFamily = "Arial, sans-serif";
    button.style.fontSize = "0.95rem";

    button.addEventListener("click", function () {
      if (typeof window.scormSetComplete === "function") {
        window.scormSetComplete();
        button.innerText = "Completed";
        button.disabled = true;
        button.style.opacity = "0.7";
        button.style.cursor = "default";
      }
    });

    document.body.appendChild(button);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", addCompletionButton);
  } else {
    addCompletionButton();
  }
})();
"""


SCORM_NAVIGATION_FIX_JS = r"""
(function () {
  function isInternalLink(link) {
    if (!link || !link.getAttribute) return false;

    var href = link.getAttribute("href");

    if (!href) return false;
    if (href.startsWith("#")) return false;
    if (href.startsWith("mailto:")) return false;
    if (href.startsWith("tel:")) return false;
    if (href.startsWith("javascript:")) return false;
    if (href.startsWith("http://")) return false;
    if (href.startsWith("https://")) return false;
    if (href.startsWith("//")) return false;

    return true;
  }

  function fixLinkTargets() {
    var links = document.querySelectorAll("a[href]");

    links.forEach(function (link) {
      if (isInternalLink(link)) {
        link.setAttribute("target", "_self");
      }
    });
  }

  function interceptInternalLinks() {
    document.addEventListener("click", function (event) {
      var link = event.target.closest ? event.target.closest("a[href]") : null;

      if (!isInternalLink(link)) return;

      var href = link.getAttribute("href");

      if (!href) return;

      event.preventDefault();
      event.stopPropagation();

      window.location.href = href;
    }, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      fixLinkTargets();
      interceptInternalLinks();
    });
  } else {
    fixLinkTargets();
    interceptInternalLinks();
  }
})();
"""


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_") or "course"


def copy_site(site_dir: Path, package_dir: Path) -> None:
    if package_dir.exists():
        shutil.rmtree(package_dir)

    shutil.copytree(
        site_dir,
        package_dir,
        ignore=shutil.ignore_patterns(
            ".DS_Store",
            "__pycache__",
            "*.pyc",
            ".quarto",
            ".git",
            ".Rproj.user",
        ),
    )


def write_scorm_scripts(package_dir: Path) -> None:
    scripts_dir = package_dir / "scorm"
    scripts_dir.mkdir(exist_ok=True)

    (scripts_dir / "scorm_api_wrapper.js").write_text(
        SCORM_API_WRAPPER_JS.strip() + "\n",
        encoding="utf-8",
    )

    (scripts_dir / "scorm_tracking.js").write_text(
        SCORM_TRACKING_JS.strip() + "\n",
        encoding="utf-8",
    )

    (scripts_dir / "scorm_navigation_fix.js").write_text(
        SCORM_NAVIGATION_FIX_JS.strip() + "\n",
        encoding="utf-8",
    )


def fix_root_relative_paths(package_dir: Path) -> int:
    changed_count = 0
    target_suffixes = {".html", ".css", ".js"}

    for file_path in package_dir.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in target_suffixes:
            continue

        text = file_path.read_text(encoding="utf-8", errors="replace")
        original = text

        text = re.sub(r'(href|src)=["\']/(?!/)', r'\1="', text)
        text = re.sub(r'url\(["\']?/(?!/)', 'url("', text)

        if text != original:
            file_path.write_text(text, encoding="utf-8")
            changed_count += 1

    return changed_count


def inject_base_target_self(package_dir: Path) -> int:
    changed_count = 0

    for html_file in package_dir.rglob("*.html"):
        text = html_file.read_text(encoding="utf-8", errors="replace")
        original = text

        if re.search(r"<base\s+", text, flags=re.IGNORECASE):
            continue

        if re.search(r"<head[^>]*>", text, flags=re.IGNORECASE):
            text = re.sub(
                r"(<head[^>]*>)",
                r'\1' + "\n" + '<base target="_self">',
                text,
                count=1,
                flags=re.IGNORECASE,
            )

        if text != original:
            html_file.write_text(text, encoding="utf-8")
            changed_count += 1

    return changed_count


def relative_scorm_path(html_file: Path, package_dir: Path) -> str:
    relative_parent = html_file.parent.relative_to(package_dir)

    if str(relative_parent) == ".":
        return "scorm"

    depth = len(relative_parent.parts)
    return "/".join([".."] * depth + ["scorm"])


def inject_scripts_into_html(package_dir: Path, inject_all_pages: bool, launch_file: str) -> int:
    html_files = list(package_dir.rglob("*.html"))

    if not inject_all_pages:
        html_files = [package_dir / launch_file]

    injected_count = 0

    for html_file in html_files:
        if not html_file.exists():
            continue

        text = html_file.read_text(encoding="utf-8", errors="replace")

        if "scorm_api_wrapper.js" in text:
            continue

        scorm_path = relative_scorm_path(html_file, package_dir)

        script_tags = f"""
<script src="{scorm_path}/scorm_api_wrapper.js"></script>
<script src="{scorm_path}/scorm_navigation_fix.js"></script>
<script src="{scorm_path}/scorm_tracking.js"></script>
""".strip()

        if re.search(r"</body\s*>", text, flags=re.IGNORECASE):
            text = re.sub(
                r"</body\s*>",
                script_tags + "\n</body>",
                text,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            text += "\n" + script_tags + "\n"

        html_file.write_text(text, encoding="utf-8")
        injected_count += 1

    return injected_count


def list_package_files(package_dir: Path) -> list[str]:
    files: list[str] = []

    for path in sorted(package_dir.rglob("*")):
        if path.is_file():
            files.append(path.relative_to(package_dir).as_posix())

    return files


def write_manifest(package_dir: Path, title: str, launch_file: str) -> None:
    safe_title = html.escape(title)
    safe_launch_file = html.escape(launch_file)

    file_entries = "\n".join(
        f'      <file href="{html.escape(file_path)}" />'
        for file_path in list_package_files(package_dir)
        if file_path != "imsmanifest.xml"
    )

    manifest = f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="MANIFEST-{slugify(title)}"
          version="1.0"
          xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd
                              http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">

  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>

  <organizations default="ORG-1">
    <organization identifier="ORG-1">
      <title>{safe_title}</title>
      <item identifier="ITEM-1" identifierref="RESOURCE-1">
        <title>{safe_title}</title>
      </item>
    </organization>
  </organizations>

  <resources>
    <resource identifier="RESOURCE-1"
              type="webcontent"
              adlcp:scormtype="sco"
              href="{safe_launch_file}">
{file_entries}
    </resource>
  </resources>
</manifest>
"""

    (package_dir / "imsmanifest.xml").write_text(manifest, encoding="utf-8")


def zip_package(package_dir: Path, output_zip: Path) -> None:
    if output_zip.exists():
        output_zip.unlink()

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                zipf.write(path, path.relative_to(package_dir).as_posix())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Package rendered Quarto HTML output as a SCORM 1.2 ZIP."
    )

    parser.add_argument(
        "--site-dir",
        required=True,
        help="Path to rendered web output folder containing index.html.",
    )

    parser.add_argument(
        "--title",
        required=True,
        help="Course title for the SCORM manifest.",
    )

    parser.add_argument(
        "--launch-file",
        default="index.html",
        help="Launch file inside the site directory. Default: index.html",
    )

    parser.add_argument(
        "--output-dir",
        default="dist_scorm",
        help="Directory for generated SCORM package folder and ZIP.",
    )

    parser.add_argument(
        "--output-zip",
        default=None,
        help="Optional custom output ZIP filename.",
    )

    parser.add_argument(
        "--launch-page-only",
        action="store_true",
        help="Inject SCORM tracking only into the launch page instead of all HTML pages.",
    )

    args = parser.parse_args()

    site_dir = Path(args.site_dir).resolve()

    if not site_dir.exists():
        raise FileNotFoundError(f"Site directory not found: {site_dir}")

    if not site_dir.is_dir():
        raise NotADirectoryError(f"Site path is not a directory: {site_dir}")

    launch_path = site_dir / args.launch_file

    if not launch_path.exists():
        raise FileNotFoundError(f"Launch file not found: {launch_path}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    package_dir = output_dir / f"{slugify(args.title)}_scorm_package"

    output_zip = (
        Path(args.output_zip).resolve()
        if args.output_zip
        else output_dir / f"{slugify(args.title)}_scorm_1_2.zip"
    )

    if output_zip.suffix.lower() != ".zip":
        output_zip = output_zip.with_suffix(".zip")

    copy_site(site_dir, package_dir)
    write_scorm_scripts(package_dir)

    fixed_path_count = fix_root_relative_paths(package_dir)
    base_target_count = inject_base_target_self(package_dir)

    injected_count = inject_scripts_into_html(
        package_dir=package_dir,
        inject_all_pages=not args.launch_page_only,
        launch_file=args.launch_file,
    )

    write_manifest(package_dir, args.title, args.launch_file)
    zip_package(package_dir, output_zip)

    print("SCORM package created successfully.")
    print(f"Source site: {site_dir}")
    print(f"SCORM working folder: {package_dir}")
    print(f"SCORM ZIP: {output_zip}")
    print(f"HTML files injected: {injected_count}")
    print(f"Files with root-relative paths fixed: {fixed_path_count}")
    print(f"HTML files with base target injected: {base_target_count}")
    print("")
    print("Upload the ZIP file to Moodle as a SCORM package activity.")


if __name__ == "__main__":
    main()