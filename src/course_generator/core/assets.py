import os
from pathlib import Path


def rewrite_asset_path(asset_path: str, qmd_path: Path, course_dir: Path) -> str:
    """
    Rewrite a site-level asset path like 'resources/pdf/file.pdf' so it works
    from the nested location of the generated QMD/HTML page.
    """
    asset_path = asset_path.strip().replace("\\", "/")

    if not asset_path.startswith("resources/"):
        return asset_path

    qmd_parent = qmd_path.parent
    target_asset = course_dir / asset_path
    relative_path = os.path.relpath(target_asset, start=qmd_parent)
    return relative_path.replace("\\", "/")
