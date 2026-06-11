# CloudPedagogy Learning Publisher

*Author once in Word. Publish interactive learning experiences with Quarto.*

CloudPedagogy Learning Publisher transforms structured Word documents into interactive Quarto-based eLearning courses, websites, handbooks, and reusable learning resources.

It bridges the gap between authoring in a familiar word processor and publishing to a modern, code-driven documentation framework. It automates the scaffolding of Quarto sites and provides a specialized parser to convert specific authoring patterns in Microsoft Word into interactive web components.

---

## ⚠️ Disclaimer

CloudPedagogy Learning Publisher is an independent exploratory tool. It is not affiliated with, endorsed by, or representative of any employer, university, or organisation. It is provided for educational, experimental, and illustrative purposes only. Users are responsible for reviewing all generated learning materials before use.

---

## Relationship to CloudPedagogy Course Engine

- **Learning Publisher** = content creation and publishing layer. It focuses on transforming structured documents into learning websites and PDFs.
- **Course Engine** = production, validation, and orchestration layer. It focuses on broader course production, reproducible builds, traceable outputs, and governance-ready course artefacts.

## The Hybrid Workflow

The application supports a powerful hybrid workflow that splits course structure from course content:

1. **Course Structure (YAML):** You define the hierarchy of your course (Modules, Sessions, Sections, Pages) in a simple YAML configuration file. 
2. **Scaffold Generation:** The `coursegen build` command uses this YAML to automatically generate a complete folder structure of Quarto `.qmd` files, complete with navigation and frontmatter.
3. **Course Content (Word):** You write your actual learning content in Microsoft Word documents (`.docx`), using a simple custom syntax to define interactive elements (like Quizzes, Reveal blocks, Tabs, and R code).
4. **Content Injection:** The `coursegen import_word` command parses your Word documents, translates the custom syntax into web-ready components, and injects the content into the Quarto scaffold.

## Key Features

- **Automated Quarto Scaffolding:** Generate hundreds of correctly structured, interlinked Quarto files from a single YAML config.
- **Word-to-Web Translation:** Write in Word, publish to HTML without touching code.
- **Interactive Component Parsing:** Native parsing for quizzes, tabs, code execution (WebR), callouts, and more.
- **Multiple Output Formats:**
  - Interactive Quarto HTML Website
  - SCORM 1.2 Packages (for LMS deployment)
  - PDF & Word Course Handbooks (automatically compiled from web content)

## Requirements

- **Python 3.10+**
- **Quarto** (latest version recommended)
- **Pandoc** (required for Word-to-Markdown conversion)
- **TinyTeX / LaTeX** (required if you wish to generate PDF handbooks)

## Installation

We recommend using a Python virtual environment.

```bash
# 1. Clone the repository
git clone <repository_url>
cd cloudpedagogy-learning-publisher

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# 3. Install the package and its dependencies
pip install -e .
```

*For more detailed setup instructions, including installing Quarto and Pandoc, see [INSTALLATION.md](docs/INSTALLATION.md).*

## Quick Start

The CLI tool is installed as `coursegen`.

```bash
# 1. Initialize a blank course template config (optional)
coursegen init --path config/my_course.yml

# 2. Build the Quarto scaffold from a config
coursegen build config/outbreak_ve_demo.yml

# 3. Import Word documents into the generated scaffold
coursegen import_word config/outbreak_ve_demo.yml

# 4. Preview a specific page during authoring
coursegen preview course/outbreak_ve_demo/se01/01-introduction/intro1.qmd

# 5. Render the final Quarto website
coursegen render config/outbreak_ve_demo.yml
```

## Additional Outputs

You can generate alternative outputs using the standalone scripts in the `src/course_generator/tools/` directory.

### Build a Course Handbook
Compiles the web content into a single PDF or Word document:
```bash
python src/course_generator/tools/build_handbook_from_quarto.py course/outbreak_ve_demo
```

### Package for SCORM 1.2
Wraps your rendered HTML site in a SCORM manifest for your LMS:
```bash
python src/course_generator/tools/package_scorm.py --site-dir output/outbreak_ve_demo --title "My Course"
```

## Documentation

For deep-dives into the architecture, commands, and workflows, please see the `docs/` folder:

- [Repository Review](docs/REPOSITORY_REVIEW.md): An analysis of the repository's current functional state.
- [Project Specification](docs/PROJECT_SPEC.md): Goals and target audience.
- [Architecture](docs/ARCHITECTURE.md): How the pipeline works under the hood.
- [Workflows](docs/WORKFLOWS.md): Detailed guides on authoring in YAML and Word.
- [Usage Reference](docs/USAGE.md): Complete CLI documentation.
- [Installation](docs/INSTALLATION.md): Detailed setup steps.
