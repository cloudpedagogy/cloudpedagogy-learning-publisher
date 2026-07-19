import yaml
import os
from pathlib import Path
from typing import Any, Dict
from ..models.schema import CourseConfig

class ConfigLoader:
    @staticmethod
    def _slugify(text: str) -> str:
        """Simple slugify for ID generation."""
        return text.lower().replace(' ', '-').replace(':', '').replace('?', '').replace(',', '').replace('.', '')

    @staticmethod
    def load(config_path: str) -> CourseConfig:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        changed = False
        
        # 1. Module ID
        module_data = data.get('module', {})
        module_code = module_data.get('code', 'module').lower()
        if 'id' not in module_data:
            module_data['id'] = module_code
            changed = True
        
        m_id = module_data['id']
        
        # 2. Sessions, Sections, and Pages
        for s_idx, session in enumerate(data.get('sessions', []), 1):
            if 'id' not in session:
                session['id'] = f"{m_id}-se{s_idx:02d}"
                changed = True
            
            s_id = session['id']
            for sec_idx, section in enumerate(session.get('sections', []), 1):
                if 'id' not in section:
                    section['id'] = f"{s_id}-sec{sec_idx:02d}"
                    changed = True
                
                sec_id = section['id']
                # Determine subpages or pages
                pages_key = 'subpages' if 'subpages' in section else 'pages'
                for p_idx, page in enumerate(section.get(pages_key, []), 1):
                    if 'id' not in page:
                        page['id'] = f"{sec_id}-sp{p_idx:02d}"
                        changed = True

        # 3. Optional course-level standalone pages
        # These pages sit beside sessions in the site navigation.
        for p_idx, page in enumerate(data.get('standalone_pages', []), 1):
            if 'id' not in page:
                page_slug = ConfigLoader._slugify(page.get('title', f'page-{p_idx}'))
                page['id'] = f"{m_id}-{page_slug}"
                changed = True
        
        # Write back if we generated any IDs
        if changed:
            with open(path, 'w') as f:
                yaml.dump(data, f, sort_keys=False, default_flow_style=False)
        
        config = CourseConfig(**data)
        
        # Validate subpage counts for all sessions/sections
        for session in config.sessions:
            for section in session.sections:
                section.validate_structure()
        return config
