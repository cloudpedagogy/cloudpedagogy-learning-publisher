import os
import shutil
import re
from pathlib import Path
from typing import Optional, Dict, List
import yaml
from .config_loader import CourseConfig
from .templates import TemplateManager
from .interaction_resolver import InteractionResolver
from .page_kind_resolver import PageKindResolver

class Generator:
    def __init__(self, config: CourseConfig, output_dir: str, templates_dir: str):
        self.config = config
        self.output_dir = Path(output_dir)
        self.templates_dir = Path(templates_dir)
        self.template_manager = TemplateManager(str(self.templates_dir))
        
        # Instantiate interaction resolver pointing to templates/interactions
        self.interaction_resolver = InteractionResolver(str(self.templates_dir))
        
        # Initialize PageKindResolver pointing to root templates/pages
        self.page_kind_resolver = PageKindResolver(str(self.templates_dir / "pages"))
        
        # Load block defaults for pedagogical scaffolding
        self.block_defaults = {}
        defaults_path = Path(__file__).parent.parent / "registry" / "block_defaults.yml"
        if defaults_path.exists():
            with open(defaults_path, 'r') as f:
                self.block_defaults = yaml.safe_load(f) or {}
        self.existing_files: Dict[str, Path] = {}

    def _scan_existing_ids(self):
        """Walk the output directory and map IDs to file paths."""
        self.existing_files = {}
        for root, _, files in os.walk(self.output_dir):
            if "_archive" in root: continue
            for file in files:
                if file.endswith(".qmd"):
                    path = Path(root) / file
                    file_id = self._get_id_from_file(path)
                    if file_id:
                        self.existing_files[file_id] = path

    def _get_id_from_file(self, path: Path) -> Optional[str]:
        """Extract ID from QMD frontmatter."""
        try:
            with open(path, 'r') as f:
                content = f.read()
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    data = yaml.safe_load(parts[1])
                    return data.get('id')
        except:
            pass
        return None

    def build(self, force: bool = False, global_render_mode: Optional[str] = None):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._scan_existing_ids()
        
        processed_ids = set()
        pages_to_generate = []
        sidebar_contents = [{"text": "Home", "href": "index.qmd"}]
        sessions_nav = []

        # 1. Module Landing
        processed_ids.add(self.config.module.id)
        pages_to_generate.append({
            "id": self.config.module.id,
            "template": "module/default/index.qmd.j2",
            "output_path": self.output_dir / "index.qmd",
            "context": {"module": self.config.module, "sessions": self.config.sessions, "role": "module_landing"},
            "title": self.config.module.title
        })

        # 2. Process Sessions
        for session in self.config.sessions:
            mode = global_render_mode or session.render_mode or self.config.module.default_render_mode
            session_dir = self.output_dir / session.code.lower()
            session_dir.mkdir(exist_ok=True)
            
            processed_ids.add(session.id)
            pages_to_generate.append({
                "id": session.id,
                "template": "session/multi_page/index.qmd.j2" if mode == "multi_page" else "session/standard/index.qmd.j2",
                "output_path": session_dir / "index.qmd",
                "context": {
                    "module": self.config.module, "session": session, "render_mode": mode, "role": "session_landing"
                },
                "title": session.title
            })

            session_nav = {"section": f"{session.code}: {session.title}", "href": f"{session.code.lower()}/index.qmd", "contents": []}

            # 3. Process Sections
            for section in session.sections:
                section_slug = self._slugify(section.title)
                section_prefix = f"sec{section.number:02d}"
                current_pages = section.effective_pages
                # A section landing page is useful only when it groups multiple
                # content pages. Single-page sections link directly to their
                # content page while retaining the learner-facing
                # "Section {number}: {title}" navigation label below.
                needs_folder = len(current_pages) > 1

                if needs_folder:
                    # Keep folder names readable (01-slug) for workspace organization
                    folder_name = f"{section.number:02d}-{section_slug}"
                    section_dir = session_dir / folder_name
                    section_dir.mkdir(exist_ok=True)
                    
                    # Section Landing
                    processed_ids.add(section.id)
                    pages_to_generate.append({
                        "id": section.id,
                        "template": "sections/section_overview.qmd.j2",
                        "output_path": section_dir / "index.qmd",
                        "context": {
                            "module": self.config.module, "session": session, "section": section,
                            "role": "section_landing", "navigation_style": section.navigation_style,
                            "breadcrumbs": [
                                {"text": self.config.module.code, "href": "../../index.qmd"},
                                {"text": session.code, "href": "../index.qmd"},
                                {"text": section.title}
                            ]
                        },
                        "title": section.title
                    })

                    section_nav_item = {"text": f"Section {section.number}: {section.title}", "contents": []}
                    section_nav_item["href"] = f"{session.code.lower()}/{folder_name}/index.qmd"

                    # Subpages
                    for p_idx, page in enumerate(current_pages, 1):
                        filename = f"{page.id}.qmd"
                        processed_ids.add(page.id)
                        
                        pages_to_generate.append({
                            "id": page.id,
                            "template": "sections/section_overview.qmd.j2",
                            "output_path": section_dir / filename,
                            "context": {
                                "module": self.config.module, "session": session, "section": section, "page": page,
                                "page_num": p_idx, "total_pages": len(current_pages), "role": "content_page",
                                "navigation_style": section.navigation_style,
                                "breadcrumbs": [
                                    {"text": self.config.module.code, "href": "../../index.qmd"},
                                    {"text": session.code, "href": "../index.qmd"},
                                    {"text": section.title, "href": "index.qmd"},
                                    {"text": page.title}
                                ]
                            },
                            "title": page.title
                        })
                        section_nav_item["contents"].append({"text": page.title, "href": f"{session.code.lower()}/{folder_name}/{filename}"})
                    session_nav["contents"].append(section_nav_item)
                else:
                    # Single file section
                    page = current_pages[0] if current_pages else None
                    page_id = page.id if page else section.id
                    filename = f"{page_id}.qmd"
                    processed_ids.add(page_id)
                    
                    pages_to_generate.append({
                        "id": page_id,
                        "template": "sections/section_overview.qmd.j2",
                        "output_path": session_dir / filename,
                        "context": {
                            "module": self.config.module, "session": session, "section": section, "page": page,
                            "role": "content_page", "navigation_style": "default",
                            "breadcrumbs": [
                                {"text": self.config.module.code, "href": "../index.qmd"},
                                {"text": session.code, "href": "index.qmd"},
                                {"text": section.title}
                            ]
                        },
                        "title": section.title
                    })
                    session_nav["contents"].append({"text": f"Section {section.number}: {section.title}", "href": f"{session.code.lower()}/{filename}"})
            
            sessions_nav.append(session_nav)
        
        sidebar_contents.extend(sessions_nav)

        # 4. Process optional course-level standalone pages. These are
        # displayed beside sessions in the sidebar rather than inside one.
        for page in self.config.standalone_pages:
            filename = f"{page.id}.qmd"
            output_path = self.output_dir / filename
            processed_ids.add(page.id)

            pages_to_generate.append({
                "id": page.id,
                "template": "pages/standalone_page.qmd.j2",
                "output_path": output_path,
                "context": {
                    "module": self.config.module,
                    "page": page,
                    "role": "content_page",
                    "navigation_style": "default",
                    "breadcrumbs": [
                        {"text": self.config.module.code, "href": "index.qmd"},
                        {"text": page.title}
                    ]
                },
                "title": page.title
            })
            sidebar_contents.append({"text": page.title, "href": filename})

        # 5. Sync Files
        for i, pg in enumerate(pages_to_generate):
            # Navigation context
            nav = {"prev": None, "next": None}
            if i > 0:
                prev = pages_to_generate[i-1]
                nav["prev"] = {"title": prev["title"], "url": os.path.relpath(prev["output_path"], pg["output_path"].parent)}
            if i < len(pages_to_generate) - 1:
                nxt = pages_to_generate[i+1]
                nav["next"] = {"title": nxt["title"], "url": os.path.relpath(nxt["output_path"], pg["output_path"].parent)}
            pg["context"]["navigation"] = nav
            
            self._sync_file(pg["id"], pg["template"], pg["output_path"], pg["context"])

        # 6. Archive Orphans
        archive_dir = self.output_dir / "_archive"
        for fid, path in self.existing_files.items():
            if fid not in processed_ids:
                archive_dir.mkdir(exist_ok=True)
                target = archive_dir / path.name
                shutil.move(path, target)
                print(f"Archived: {path} -> {target}")

        # 7. Final Quarto/CSS
        self._generate_file("module/default/_quarto.yml.j2", self.output_dir / "_quarto.yml", {"module": self.config.module, "sidebar_contents": sidebar_contents}, force=True)
        self._generate_file("styles.css.j2", self.output_dir / "styles.css", {}, force=True)

        # 8. Cleanup empty folders
        for root, dirs, _ in os.walk(self.output_dir, topdown=False):
            if "_archive" in root or "assets" in root: continue
            for d in dirs:
                d_path = os.path.join(root, d)
                if not os.listdir(d_path):
                    os.rmdir(d_path)
                    print(f"Cleaned up empty folder: {d_path}")

    def _sync_file(self, file_id: str, template_name: str, target_path: Path, context: Dict):
        """Sync a file: move if needed, update frontmatter, preserve body."""
        existing_path = self.existing_files.get(file_id)
        
        role = context.get("role", "content_page")
        is_landing = role in ["module_landing", "session_landing", "section_landing"]
        
        # 0. Extract existing interaction data if it exists
        IT_START = "<!-- START_INTERACTIONS -->"
        IT_END = "<!-- END_INTERACTIONS -->"
        existing_interaction_data = {}
        
        if existing_path and existing_path.exists():
            with open(existing_path, 'r') as f:
                body_all = f.read()
                if IT_START in body_all and IT_END in body_all:
                    it_block = body_all.split(IT_START)[1].split(IT_END)[0]
                    existing_interaction_data = self._extract_interaction_data(it_block)

        # Consolidate interaction list from context
        interactions = []
        if "page" in context and hasattr(context["page"], "interactions"):
            interactions.extend(context["page"].interactions)
        
        # If it's a landing page OR a single-page section, include its primary object's interactions
        if role == "section_landing" and "section" in context:
            interactions.extend(context["section"].interactions)
        elif role == "session_landing" and "session" in context:
            interactions.extend(context["session"].interactions)
        elif role == "module_landing" and "module" in context:
            interactions.extend(context["module"].interactions)
        elif role == "content_page" and "section" in context:
            if len(context["section"].effective_pages) <= 1:
                for it in context["section"].interactions:
                    if it not in interactions:
                        interactions.append(it)

        # 1. Resolve Interactions into an ordered list
        rendered_interactions = self.interaction_resolver.resolve_page_interactions(
            interactions, existing_data=existing_interaction_data
        )
        
        # Join into a single block with horizontal separators
        IT_START = "<!-- START_INTERACTIONS -->"
        IT_END = "<!-- END_INTERACTIONS -->"
        
        interactions_content = ""
        if rendered_interactions:
            joined = "\n\n---\n\n".join(rendered_interactions)
            interactions_content = f"\n\n---\n\n{IT_START}\n{joined}\n{IT_END}\n"

        # 2. Resolve Page Scaffold for content pages
        page_obj = context.get("page")
        kind = page_obj.kind if page_obj else None
        page_scaffold = ""
        
        if role == "content_page":
            title = page_obj.title if page_obj else "this page"
            page_id = page_obj.id if page_obj else ""
            
            # Prepare scaffold context with pedagogy prompts
            # Note: We NO LONGER apply decorators here. Everything is a sequential interaction now.
            scaffold_context = {"title": title, "id": page_id}
            
            # Get default blocks for this kind
            kind_defaults = self.block_defaults.get(kind, {})
            for block_id, default_prompt in kind_defaults.items():
                scaffold_context[block_id] = default_prompt
            
            page_scaffold = self.page_kind_resolver.render_scaffold(kind, scaffold_context)
            
        # Add resources to context
        resources_content = ""
        if page_obj:
            resources_content = self._handle_resources(page_obj, target_path)

        # Add interactions to context for landing page templates too
        context["interactions"] = interactions_content
        context["page_contents"] = page_scaffold
        context["resources_content"] = resources_content

        # Resolve navigation block
        nav_block = ""
        if context.get("navigation"):
            nav_block = self.template_manager.render("nav/page_nav.qmd.j2", context)

        if existing_path and existing_path.exists():
            # Move if path changed
            if existing_path != target_path:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(existing_path, target_path)
                print(f"Moved: {existing_path} -> {target_path}")
            
            # Update metadata but preserve body
            if is_landing:
                # Landing pages are fully template-driven
                content = self.template_manager.render(template_name, context)
                
                # Append nav at the bottom of landing pages
                if nav_block:
                    content = content.rstrip() + "\n\n" + nav_block + "\n"

                with open(target_path, 'w') as f:
                    f.write(content)
                print(f"Updated landing page: {target_path}")
            else:
                with open(target_path, 'r') as f:
                    current_content = f.read()
                
                # Accurate split of Frontmatter and Body
                import re
                # Find the very last '---' that terminates the frontmatter section
                # We look for the first two occurrences of '---' at the start of lines
                fm_pattern = r'^---\s*\n.*?\n---\s*\n'
                fm_match = re.search(fm_pattern, current_content, re.DOTALL)
                
                if fm_match:
                    body = current_content[fm_match.end():]
                    # Aggressively clean up any lingering frontmatter-like dashes at the start of the body
                    body = re.sub(r'^(---\s*\n)+', '', body).strip()
                else:
                    body = current_content.strip()

                # 0. Cleanup ALL Navigation markers (new and legacy)
                nav_marker_pattern = r'\n*<!-- START_NAVIGATION -->.*?<!-- END_NAVIGATION -->\n*'
                body = re.sub(nav_marker_pattern, '', body, flags=re.DOTALL)
                legacy_nav_pattern = r'\n*```\{=html\}\n<div class="custom-page-navigation">.*?</div>\n```\n*'
                body = re.sub(legacy_nav_pattern, '', body, flags=re.DOTALL).strip()
                
                # 1. Handle Interaction Block Update
                IT_START = "<!-- START_INTERACTIONS -->"
                IT_END = "<!-- END_INTERACTIONS -->"
                # (Existing interaction logic remains same...)
                
                if IT_START in body and IT_END in body:
                    pre = body.split(IT_START)[0].rstrip()
                    # Clean up any trailing separator before the marker if we have new content
                    import re
                    if interactions_content:
                        pre = re.sub(r'\n\n---\s*$', '', pre, flags=re.MULTILINE).rstrip()
                    
                    post = body.split(IT_END)[1]
                    body = pre + interactions_content + post.lstrip()
                elif interactions_content:
                    # If marker not found, append at end of body
                    body = body.rstrip() + interactions_content

                # 2. Update Navigation Block (ensure it's at the absolute bottom)
                NAV_START = "<!-- START_NAVIGATION -->"
                NAV_END = "<!-- END_NAVIGATION -->"
                # Strip existing navigation blocks and append to bottom
                nav_pattern = r'\n\n<!-- START_NAVIGATION -->.*?<!-- END_NAVIGATION -->\n?'
                body = re.sub(nav_pattern, '', body, flags=re.DOTALL).rstrip()
                if nav_block:
                    body = body.rstrip() + f"\n\n{NAV_START}\n\n{nav_block}\n{NAV_END}\n"

                new_frontmatter_rendered = self.template_manager.render(template_name, context)
                # Extract JUST the YAML from the rendered template
                import re
                fm_match = re.search(r'^---\n(.*?)\n---\n?', new_frontmatter_rendered, re.DOTALL)
                new_fm_content = fm_match.group(1) if fm_match else ""
                
                # Combine into the final file content
                final_content = f"---\n{new_fm_content}\n---\n{body}"
                with open(target_path, 'w') as f:
                    f.write(final_content)
                print(f"Updated metadata: {target_path}")
        else:
            # New file
            target_path.parent.mkdir(parents=True, exist_ok=True)
            content = self.template_manager.render(template_name, context)
            
            # In any case, ensures the interaction content is in the body if it wasn't in the scaffold
            # But normally, our new scaffolds will have it.
            if interactions_content and "<!-- START_INTERACTIONS -->" not in content:
                content = content.rstrip() + interactions_content
            
            # Inject navigation block at the very end
            if nav_block:
                NAV_START = "<!-- START_NAVIGATION -->"
                NAV_END = "<!-- END_NAVIGATION -->"
                # Avoid redundant separator (CSS handles it)
                content = content.rstrip() + f"\n\n{NAV_START}\n\n{nav_block}\n{NAV_END}\n"
                
            with open(target_path, 'w') as f:
                f.write(content)
            print(f"Generated new: {target_path}")

    def _generate_file(self, template_name: str, output_path: Path, context: dict, force: bool):
        if output_path.exists() and not force: return
        content = self.template_manager.render(template_name, context)
        with open(output_path, 'w') as f: f.write(content)
        print(f"Generated: {output_path}")

    def _handle_resources(self, page, target_path: Path) -> str:
        """
        Processes resources for a page:
        1. Copies files from root 'resources/' to '<target_dir>/files/'.
        2. Renders a resource block partial and returns the context.
        """
        if not hasattr(page, 'resources') or not page.resources:
            return ""

        target_files_dir = target_path.parent / "files"
        target_files_dir.mkdir(exist_ok=True)
        
        remapped_resources = []
        for res in page.resources:
            source_path = Path(res.file)
            if not source_path.exists():
                print(f"Warning: Resource file {source_path} not found. Skipping.")
                continue
            
            # Copy file to local 'files/' directory
            dest_path = target_files_dir / res.output_file
            shutil.copy2(source_path, dest_path)
            
            # Record for context (path relative to the .qmd)
            remapped_resources.append({
                "title": res.title,
                "path": f"files/{res.output_file}",
                "display": res.display,
                "ext": dest_path.suffix.lower().lstrip('.')
            })
        
        if not remapped_resources:
            return ""
            
        # Render the resource block using the partial
        return self.template_manager.render("nav/resource_block.qmd.j2", {"resources": remapped_resources})

    def _slugify(self, text: str) -> str:
        return text.lower().replace(' ', '-').replace(':', '').replace('?', '').replace(',', '').replace('.', '')

    def _extract_interaction_data(self, it_block: str) -> Dict[int, Dict[str, str]]:
        """
        Parses an existing interaction block and extracts content from editable zones.
        Returns a dictionary indexed by interaction index (0-based) containing zone_id -> content mappings.
        """
        import re
        # We assume interactions are separated by '---' (with optional whitespace)
        # However, the first and last parts might not have the separator if it's just one interaction.
        # But our Generator adds '---' between them.
        raw_interactions = re.split(r'\n\n---\n\n', it_block.strip())
        
        data = {}
        zone_pattern = re.compile(r'<!-- editable:start\s+(?P<zone_id>[\w_]+)\s+-->(?P<content>.*?)<!-- editable:end -->', re.DOTALL)
        
        for i, it_text in enumerate(raw_interactions):
            zones = {}
            for match in zone_pattern.finditer(it_text):
                zone_id = match.group('zone_id')
                content = match.group('content').strip()
                # Only sync if it's not a placeholder (Author Guide) 
                # or if the user wants us to ALWAYS preserve it once edited.
                # We'll preserve it if it DOES NOT contain the "[AUTHOR GUIDE:" prefix
                if "[AUTHOR GUIDE:" not in content:
                    zones[zone_id] = content
            
            if zones:
                data[i] = zones
        return data

    # [DEPRECATED] Positional injection is replaced by ordered sequence in {{ interactions }}
    def _inject_positional_interactions(self, body: str, inserted_blocks: Dict[str, List[str]]) -> str:
        return body
