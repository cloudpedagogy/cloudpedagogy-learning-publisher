# Project Roadmap: CloudPedagogy Learning Publisher

Based on the current state of the repository, this document outlines recommendations for future development, positioning, and codebase cleanup.

## 1. Future Positioning: Relationship with Course Engine

Currently, the Learning Publisher operates as an independent, standalone pipeline. Its primary capability is content transformation (Word/YAML -> Quarto).

However, the broader **CloudPedagogy Course Engine** project is focused on production, validation, and orchestration.

**Recommendation:** 
The Learning Publisher should remain a standalone repository for the immediate future to allow rapid iteration on the Word parsing logic and Quarto scaffolding. However, its CLI commands should eventually be designed so they can be seamlessly consumed as automated steps within the larger Course Engine CI/CD orchestration layer.

## 2. Codebase Cleanup and Consolidation

### Integrate Standalone Tools into the CLI
Currently, generating secondary outputs requires invoking standalone Python scripts:
- `src/course_generator/tools/package_scorm.py`
- `src/course_generator/tools/build_handbook_from_quarto.py`

**Recommendation:** 
Consolidate these into the main `coursegen` CLI to provide a unified user experience. 
*Proposed commands:*
- `coursegen package-scorm config/course.yml`
- `coursegen build-handbook config/course.yml`

### Legacy Template Cleanup
The directory `templates/interactions/` contains Jinja2 templates for interactive components. However, the current Word import workflow (`import_word.py`) generates its own HTML and Markdown for these interactions directly via Python functions (e.g., `parse_quiz`).

**Recommendation:** 
Audit the usage of `templates/interactions/`. If the direct authoring workflow no longer relies on these Jinja partials, they should be archived to prevent confusion and maintain a single source of truth for component markup (the Python parsers).

## 3. Enhancements to the Word Importer

The `import_word.py` script is highly functional but relies on rigid, hardcoded regular expressions.

**Recommendations:**
- **Robust Parsing:** Migrate from simple regex line-matching to a more robust, state-based Markdown parser to handle edge cases in Word formatting more gracefully.
- **Syntax Documentation Generation:** Automate the generation of a "Word Authoring Guide" directly from the parser logic to ensure the documentation of the custom syntax (e.g., `Option ::`) never drifts out of sync with the code.
- **Enhanced Validation:** Expand the `validate_import_content` function to catch more authoring errors (e.g., missing assets, unclosed blocks) before injecting into the Quarto scaffold.
