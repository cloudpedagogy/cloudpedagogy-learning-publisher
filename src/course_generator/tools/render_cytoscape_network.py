#!/usr/bin/env python3
"""Render generic Word network data as an interactive Cytoscape.js page.

Expected Word headings and table columns (schema 1.0):

NETWORK: field, value
NODES:   id, label, type, group, description, color, shape, status
EDGES:   id, source, target, relationship, label, directed, weight, status

Incomplete edge rows are ignored. Required node fields are id and label.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.document import Document as DocumentObject
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P


SCHEMA_VERSION = "1.0"
DEFAULT_OUTPUT_ROOT = Path("output/cytoscape_networks")
CYTOSCAPE_CDN = "https://cdn.jsdelivr.net/npm/cytoscape@3.30.4/dist/cytoscape.min.js"

NETWORK_COLUMNS = {"field", "value"}
NODE_COLUMNS = {"id", "label"}
EDGE_COLUMNS = {"id", "source", "target"}

ALLOWED_LAYOUTS = {
    "cose", "circle", "grid", "breadthfirst", "concentric", "random", "preset"
}
ALLOWED_SHAPES = {
    "ellipse", "triangle", "rectangle", "round-rectangle", "bottom-round-rectangle",
    "cut-rectangle", "barrel", "rhomboid", "diamond", "round-diamond", "pentagon",
    "round-pentagon", "hexagon", "round-hexagon", "concave-hexagon", "heptagon",
    "round-heptagon", "octagon", "round-octagon", "star", "tag", "round-tag", "vee"
}


class NetworkInputError(ValueError):
    """Raised when the Word source does not satisfy the input contract."""


def iter_blocks(document: DocumentObject) -> Iterable[Paragraph | Table]:
    """Yield document paragraphs and tables in their original order."""
    body = document.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def slug(value: str, fallback: str = "network") -> str:
    result = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return result or fallback


def table_records(table: Table) -> tuple[list[str], list[dict[str, str]]]:
    if not table.rows:
        return [], []
    headers = [slug(clean(cell.text), "column") for cell in table.rows[0].cells]
    if len(headers) != len(set(headers)):
        raise NetworkInputError(f"Duplicate table headers: {headers}")

    records: list[dict[str, str]] = []
    for row in table.rows[1:]:
        values = [clean(cell.text) for cell in row.cells]
        record = dict(zip(headers, values))
        if any(record.values()):
            records.append(record)
    return headers, records


def extract_named_tables(path: Path) -> dict[str, tuple[list[str], list[dict[str, str]]]]:
    document = Document(path)
    wanted = {"NETWORK", "NODES", "EDGES"}
    pending: str | None = None
    found: dict[str, tuple[list[str], list[dict[str, str]]]] = {}

    for block in iter_blocks(document):
        if isinstance(block, Paragraph):
            text = clean(block.text).upper()
            pending = text if text in wanted else pending
        elif isinstance(block, Table) and pending:
            if pending in found:
                raise NetworkInputError(f"More than one table found for heading {pending}.")
            found[pending] = table_records(block)
            pending = None

    missing = wanted - found.keys()
    if missing:
        raise NetworkInputError(f"Missing required heading/table: {', '.join(sorted(missing))}")
    return found


def parse_bool(value: str, default: bool = False) -> bool:
    if not clean(value):
        return default
    normal = clean(value).lower()
    if normal in {"true", "yes", "1"}:
        return True
    if normal in {"false", "no", "0"}:
        return False
    raise NetworkInputError(f"Expected true or false, received: {value!r}")


def parse_weight(value: str) -> float | None:
    if not clean(value):
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise NetworkInputError(f"Edge weight must be numeric, received: {value!r}") from exc


def require_columns(name: str, headers: list[str], required: set[str]) -> None:
    missing = required - set(headers)
    if missing:
        raise NetworkInputError(f"{name} table is missing columns: {', '.join(sorted(missing))}")


def parse_network(path: Path) -> dict:
    tables = extract_named_tables(path)
    network_headers, network_rows = tables["NETWORK"]
    node_headers, node_rows = tables["NODES"]
    edge_headers, edge_rows = tables["EDGES"]

    require_columns("NETWORK", network_headers, NETWORK_COLUMNS)
    require_columns("NODES", node_headers, NODE_COLUMNS)
    require_columns("EDGES", edge_headers, EDGE_COLUMNS)

    metadata = {clean(row.get("field", "")).lower(): clean(row.get("value", "")) for row in network_rows}
    version = metadata.get("schema_version", "")
    if version != SCHEMA_VERSION:
        raise NetworkInputError(
            f"Unsupported schema_version {version!r}; this script supports {SCHEMA_VERSION}."
        )

    network_id = slug(metadata.get("network_id", path.stem))
    title = metadata.get("title") or network_id.replace("_", " ").title()
    layout = clean(metadata.get("layout", "cose")).lower() or "cose"
    if layout not in ALLOWED_LAYOUTS:
        raise NetworkInputError(
            f"Unsupported layout {layout!r}. Choose: {', '.join(sorted(ALLOWED_LAYOUTS))}."
        )
    default_directed = parse_bool(metadata.get("default_directed", "false"))

    nodes: list[dict] = []
    node_ids: set[str] = set()
    for row_number, row in enumerate(node_rows, start=2):
        node_id = clean(row.get("id", ""))
        label = clean(row.get("label", ""))
        if not node_id and not label:
            continue
        if not node_id or not label:
            raise NetworkInputError(f"NODES row {row_number}: id and label are required.")
        if node_id in node_ids:
            raise NetworkInputError(f"Duplicate node id: {node_id}")
        node_ids.add(node_id)

        shape = clean(row.get("shape", "ellipse")).lower() or "ellipse"
        if shape not in ALLOWED_SHAPES:
            raise NetworkInputError(f"Node {node_id}: unsupported shape {shape!r}.")
        status = clean(row.get("status", "verified")).lower() or "verified"
        data = {
            "id": node_id,
            "label": label,
            "type": clean(row.get("type", "node")) or "node",
            "group": clean(row.get("group", "")),
            "description": clean(row.get("description", "")),
            "color": clean(row.get("color", "#7aa6d9")) or "#7aa6d9",
            "shape": shape,
            "status": status,
        }
        nodes.append({"data": data})

    if not nodes:
        raise NetworkInputError("The NODES table does not contain any usable nodes.")

    edges: list[dict] = []
    edge_ids: set[str] = set()
    ignored_edges = 0
    for row_number, row in enumerate(edge_rows, start=2):
        edge_id = clean(row.get("id", ""))
        source = clean(row.get("source", ""))
        target = clean(row.get("target", ""))
        if not source or not target:
            ignored_edges += 1
            continue
        if not edge_id:
            raise NetworkInputError(f"EDGES row {row_number}: id is required when source and target are set.")
        if edge_id in edge_ids:
            raise NetworkInputError(f"Duplicate edge id: {edge_id}")
        if source not in node_ids or target not in node_ids:
            unknown = source if source not in node_ids else target
            raise NetworkInputError(f"Edge {edge_id}: unknown node id {unknown!r}.")
        edge_ids.add(edge_id)

        directed = parse_bool(row.get("directed", ""), default_directed)
        weight = parse_weight(row.get("weight", ""))
        data = {
            "id": edge_id,
            "source": source,
            "target": target,
            "relationship": clean(row.get("relationship", "relates_to")) or "relates_to",
            "label": clean(row.get("label", "")),
            "directed": directed,
            "weight": weight,
            "status": clean(row.get("status", "verified")).lower() or "verified",
        }
        edges.append({"data": data})

    return {
        "schema_version": version,
        "network": {
            "id": network_id,
            "title": title,
            "description": metadata.get("description", ""),
            "layout": layout,
            "default_directed": default_directed,
            "source_file": path.name,
        },
        "elements": {"nodes": nodes, "edges": edges},
        "summary": {
            "nodes": len(nodes),
            "edges": len(edges),
            "incomplete_edges_ignored": ignored_edges,
        },
    }


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <script src="__CYTOSCAPE_CDN__"></script>
  <style>
    :root { --ink:#18324a; --muted:#5d6b78; --line:#d8e0e7; --panel:#f7f9fb; }
    * { box-sizing:border-box; }
    html, body { width:100%; height:100%; margin:0; font-family:Arial, sans-serif; color:var(--ink); }
    body { display:grid; grid-template-rows:auto 1fr; background:#fff; }
    header { display:flex; gap:16px; align-items:center; flex-wrap:wrap; padding:12px 16px; border-bottom:1px solid var(--line); }
    .titles { min-width:220px; flex:1; }
    h1 { margin:0; font-size:1.15rem; }
    #description { margin:4px 0 0; color:var(--muted); font-size:.85rem; }
    .controls { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    input, select, button { font:inherit; padding:7px 9px; border:1px solid #aebbc6; border-radius:5px; background:#fff; }
    button { cursor:pointer; }
    main { min-height:0; display:grid; grid-template-columns:minmax(0,1fr) 290px; }
    #cy { min-width:0; min-height:420px; }
    aside { border-left:1px solid var(--line); background:var(--panel); padding:14px; overflow:auto; }
    aside h2 { margin:0 0 8px; font-size:1rem; }
    aside p { font-size:.88rem; line-height:1.4; overflow-wrap:anywhere; }
    .meta { color:var(--muted); }
    .badge { display:inline-block; margin:0 5px 5px 0; padding:3px 7px; border-radius:999px; background:#e4ebf1; font-size:.75rem; }
    #empty-note { display:none; position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); padding:10px 14px; background:#fff; border:1px solid var(--line); border-radius:6px; }
    @media (max-width:760px) { main { grid-template-columns:1fr; grid-template-rows:minmax(420px,1fr) auto; } aside { border-left:0; border-top:1px solid var(--line); max-height:220px; } }
  </style>
</head>
<body>
  <header>
    <div class="titles"><h1 id="title"></h1><p id="description"></p></div>
    <div class="controls">
      <input id="search" type="search" placeholder="Search nodes" aria-label="Search nodes">
      <select id="group-filter" aria-label="Filter by group"><option value="">All groups</option></select>
      <button id="reset" type="button">Reset</button>
      <button id="fit" type="button">Fit</button>
    </div>
  </header>
  <main>
    <div id="cy" role="img" aria-label="Interactive network diagram"><div id="empty-note">No verified connections have been added yet.</div></div>
    <aside aria-live="polite">
      <h2 id="detail-title">Network information</h2>
      <div id="detail-body"></div>
    </aside>
  </main>
  <script>
    const networkData = __NETWORK_DATA__;
    const network = networkData.network;
    const allElements = [...networkData.elements.nodes, ...networkData.elements.edges];
    document.getElementById('title').textContent = network.title;
    document.getElementById('description').textContent = network.description || '';

    const namedColors = { blue:'#8ab4f8', yellow:'#fff2a6', pink:'#ee88d5', teal:'#91e2d7', grey:'#d9e1e8', gray:'#d9e1e8' };
    const colorFor = value => namedColors[String(value || '').toLowerCase()] || value || '#8ab4f8';

    const cy = cytoscape({
      container: document.getElementById('cy'),
      elements: allElements,
      layout: { name: network.layout || 'cose', animate:false, padding:40 },
      style: [
        { selector:'node', style:{
          'label':'data(label)', 'background-color': e => colorFor(e.data('color')),
          'shape':'data(shape)', 'width':'label', 'height':'label', 'padding':'12px',
          'font-size':'11px', 'text-wrap':'wrap', 'text-max-width':'150px',
          'text-valign':'center', 'text-halign':'center', 'border-width':1, 'border-color':'#52697c'
        }},
        { selector:'node[status != "verified"]', style:{ 'border-style':'dashed', 'opacity':.82 }},
        { selector:'edge', style:{
          'width': e => Math.max(1, Number(e.data('weight')) || 1),
          'line-color':'#8293a1', 'curve-style':'bezier', 'label':'data(label)',
          'font-size':'9px', 'text-rotation':'autorotate', 'text-background-color':'#fff',
          'text-background-opacity':.85, 'text-background-padding':'2px',
          'target-arrow-shape': e => e.data('directed') ? 'triangle' : 'none',
          'target-arrow-color':'#8293a1'
        }},
        { selector:'.faded', style:{ 'opacity':.10, 'text-opacity':.05 }},
        { selector:'.matched', style:{ 'border-width':4, 'border-color':'#d54b4b' }},
        { selector:':selected', style:{ 'border-width':4, 'border-color':'#173f5f' }}
      ]
    });

    const detailTitle = document.getElementById('detail-title');
    const detailBody = document.getElementById('detail-body');
    const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

    function showNetworkInfo() {
      detailTitle.textContent = 'Network information';
      detailBody.innerHTML = `<p>${esc(network.description || 'No description provided.')}</p>
        <p class="meta">${networkData.summary.nodes} nodes · ${networkData.summary.edges} connections</p>`;
    }
    function showElement(ele) {
      const d = ele.data();
      detailTitle.textContent = d.label || d.id;
      if (ele.isNode()) {
        const neighbours = ele.connectedEdges().length;
        detailBody.innerHTML = `<p>${esc(d.description || 'No description provided.')}</p>
          <span class="badge">${esc(d.type || 'node')}</span>
          ${d.group ? `<span class="badge">${esc(d.group)}</span>` : ''}
          <p class="meta">${neighbours} connection${neighbours === 1 ? '' : 's'} · ${esc(d.status)}</p>`;
      } else {
        detailBody.innerHTML = `<p><strong>${esc(d.source)}</strong> → <strong>${esc(d.target)}</strong></p>
          <span class="badge">${esc(d.relationship)}</span>
          <p class="meta">${d.directed ? 'Directed' : 'Undirected'} · ${esc(d.status)}</p>`;
      }
    }

    cy.on('tap', 'node, edge', event => {
      const ele = event.target;
      cy.elements().addClass('faded');
      if (ele.isNode()) ele.closedNeighborhood().removeClass('faded');
      else ele.connectedNodes().union(ele).removeClass('faded');
      showElement(ele);
    });
    cy.on('tap', event => { if (event.target === cy) resetView(); });

    const groups = [...new Set(networkData.elements.nodes.map(n => n.data.group).filter(Boolean))].sort();
    const groupFilter = document.getElementById('group-filter');
    groups.forEach(group => { const option=document.createElement('option'); option.value=group; option.textContent=group; groupFilter.appendChild(option); });

    function applyFilters() {
      const query = document.getElementById('search').value.trim().toLowerCase();
      const group = groupFilter.value;
      cy.nodes().forEach(node => {
        const text = `${node.data('label')} ${node.data('description')} ${node.data('type')} ${node.data('group')}`.toLowerCase();
        const matches = (!query || text.includes(query)) && (!group || node.data('group') === group);
        node.toggleClass('matched', Boolean(query) && matches);
        node.style('display', matches ? 'element' : 'none');
      });
      cy.edges().forEach(edge => edge.style('display', edge.source().visible() && edge.target().visible() ? 'element' : 'none'));
      cy.fit(cy.elements(':visible'), 40);
    }
    function resetView() {
      document.getElementById('search').value=''; groupFilter.value='';
      cy.elements().removeClass('faded matched').style('display','element');
      cy.layout({ name:network.layout || 'cose', animate:false, padding:40 }).run();
      showNetworkInfo();
    }
    document.getElementById('search').addEventListener('input', applyFilters);
    groupFilter.addEventListener('change', applyFilters);
    document.getElementById('reset').addEventListener('click', resetView);
    document.getElementById('fit').addEventListener('click', () => cy.fit(cy.elements(':visible'), 40));
    document.getElementById('empty-note').style.display = networkData.summary.edges ? 'none' : 'block';
    showNetworkInfo();
  </script>
</body>
</html>
'''


def render_html(data: dict) -> str:
    embedded = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = str(data["network"]["title"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        HTML_TEMPLATE
        .replace("__TITLE__", title)
        .replace("__CYTOSCAPE_CDN__", CYTOSCAPE_CDN)
        .replace("__NETWORK_DATA__", embedded)
    )


def output_dir_for(data: dict, output_root: Path) -> Path:
    return output_root / data["network"]["id"]


def render_one(source: Path, output_root: Path, overwrite: bool) -> Path:
    data = parse_network(source)
    destination = output_dir_for(data, output_root)
    if destination.exists() and not overwrite:
        raise NetworkInputError(
            f"Output already exists: {destination}. Use --overwrite to replace generated files."
        )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "network-data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "index.html").write_text(render_html(data), encoding="utf-8")
    return destination


def input_files(source: Path) -> list[Path]:
    if source.is_file():
        if source.suffix.lower() != ".docx":
            raise NetworkInputError("The input file must be a .docx file.")
        return [source]
    if source.is_dir():
        return sorted(p for p in source.glob("*.docx") if not p.name.startswith("~$"))
    raise NetworkInputError(f"Input does not exist: {source}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert generic Word network tables into Cytoscape.js HTML."
    )
    parser.add_argument("input", type=Path, help="A .docx file or a directory of .docx files")
    parser.add_argument(
        "--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT,
        help=f"Output root (default: {DEFAULT_OUTPUT_ROOT})"
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace generated index.html and network-data.json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        files = input_files(args.input)
        if not files:
            raise NetworkInputError(f"No .docx files found in {args.input}")
        for source in files:
            destination = render_one(source, args.output_root, args.overwrite)
            data = json.loads((destination / "network-data.json").read_text(encoding="utf-8"))
            summary = data["summary"]
            print(
                f"Rendered {source.name} -> {destination / 'index.html'} "
                f"({summary['nodes']} nodes, {summary['edges']} edges, "
                f"{summary['incomplete_edges_ignored']} incomplete edges ignored)"
            )
        return 0
    except (NetworkInputError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())