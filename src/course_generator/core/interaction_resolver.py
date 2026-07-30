import yaml
import os
from pathlib import Path
from typing import Dict, Optional
from jinja2 import Environment, FileSystemLoader

class InteractionResolver:
    """Resolves interaction types to QMD templates and renders them using a registry."""

    def __init__(self, templates_dir: str):
        self.templates_dir = Path(templates_dir)
        self.interactions_dir = self.templates_dir / "interactions"
        self.registry_path = self.interactions_dir / "interactions.yml"

        if not self.registry_path.exists():
            # Fallback for now if not yet created
            self.registry = {}
        else:
            with open(self.registry_path, 'r') as f:
                data = yaml.safe_load(f)
                # Support both "interactions" and "interaction_registry" top-level keys
                self.registry = data.get("interactions") or data.get("interaction_registry") or {}
                # Load variant registry
                self.variant_registry = data.get("interaction_variants") or {}

        self.env = Environment(
            loader=FileSystemLoader(str(self.interactions_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )

    ALIASES = {
        "detailed_explanation": "accordion_explanation",
        "accordion": "accordion_explanation",
        "tabs": "compare_tabs",
        "tabs_comparison": "compare_tabs",
        "reveal": "reveal_sequence",
        "disclosure": "reveal_sequence",
        "quiz": "quiz_check",
        "assessment": "quiz_check",
        "reflection": "reflection_prompt",
        "video": "guided_video",
        "figure": "annotated_figure",
        "interpretation": "interpretation_prompt",
        "checkpoint": "decision_checkpoint",
        "scenario": "scenario_response",
        "code": "code_example",
        "calculation": "worked_calculation",
        "math": "math_explanation",
        "exploration": "parameter_exploration"
    }

    def _resolve_type(self, it_type: str) -> str:
        """Resolves an interaction type name, handling aliases."""
        return self.ALIASES.get(it_type, it_type)

    def _resolve_variant(self, it_type: str, variant: Optional[str]) -> Optional[str]:
        """Validates and resolves a variant for a given interaction type."""
        if it_type not in self.variant_registry:
            return variant
            
        rules = self.variant_registry[it_type]
        default = rules.get("default")
        allowed = rules.get("allowed", [])
        
        if not variant or variant not in allowed:
            if variant and variant not in allowed:
                print(f"Warning: Invalid variant '{variant}' for interaction '{it_type}'. Falling back to '{default}'.")
            return default
            
        return variant

    def resolve_page_interactions(self, interactions_config: list, existing_data: Optional[Dict] = None) -> list:
        """
        Renders interactions in the order they appear in the config.
        existing_data: dict of (index -> {zone_id -> content}) to preserve.
        """
        rendered_list = []
        if not interactions_config:
            return rendered_list

        for i, it in enumerate(interactions_config):
            raw_type = it.get("type")
            it_type = self._resolve_type(raw_type)
            
            if it_type not in self.registry:
                print(f"Warning: Interaction type '{raw_type}' (resolved: '{it_type}') not found in registry.")
                continue

            # Check for existing author content for this interaction index
            it_existing = (existing_data or {}).get(i, {})
            
            # Render the interaction with merged existing data
            rendered_interaction = self.render_interaction(it_type, it, existing_data=it_existing)
            if rendered_interaction:
                rendered_list.append(rendered_interaction)

        return rendered_list

    def render_interaction(self, it_type: str, params: dict, existing_data: Optional[Dict] = None) -> str:
        """Renders an interaction using its template."""
        it_type = self._resolve_type(it_type)
        if it_type not in self.registry:
            return ""

        info = self.registry[it_type]
        template_name = info.get("template")
        if not template_name:
            return ""
        
        try:
            template = self.env.get_template(template_name)
            
            # Merit global defaults from registry into the render context
            render_context = info.copy()
            render_context.update(params)
            
            # Resolve and validate variant
            raw_variant = params.get("variant")
            render_context["variant"] = self._resolve_variant(it_type, raw_variant)
            
            # MERGE existing author content if present
            if existing_data:
                render_context.update(existing_data)
            
            return template.render(**render_context).strip()
        except Exception as e:
            print(f"Error rendering interaction '{it_type}': {e}")
            return f"\n\n::: {{.callout-warning}}\n**Error rendering interaction '{it_type}'**\n{e}\n:::\n\n"

    # --- DEPRECATED METHODS (Maintained for temporary compatibility during refactor) ---
    def render_decorator(self, it_type: str, content: str, params: dict) -> str:
        """[DEPRECATED] Wraps content with a decorator interaction."""
        params_with_content = params.copy()
        params_with_content["content"] = content
        return self.render_interaction(it_type, params_with_content)

    def render_component(self, it_type: str, params: dict) -> str:
        """[DEPRECATED] Renders an inserted component interaction."""
        return self.render_interaction(it_type, params)
