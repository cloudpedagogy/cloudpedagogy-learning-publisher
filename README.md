# CloudPedagogy Learning Publisher

CloudPedagogy Learning Publisher is a Word-first publishing system for creating accessible, maintainable e-learning with Quarto. Educators can author content in Microsoft Word while the platform handles course structure, interaction conversion, navigation, resources and publication.

The system layers a structured publishing workflow on top of Quarto. Authors do not need to write Quarto Markdown directly for routine course development.

## What it produces

Depending on the workflow and configuration, the project supports:

- Multi-page Quarto learning websites
- Printable HTML and PDF handbooks
- RevealJS presentations
- Twine scenarios
- Moodle Book conversion and quality assurance
- Moodle course audit reports
- Interactive R activities using WebR
- Mermaid diagrams and Plotly visualisations
- Custom standalone HTML interactions

## Publishing workflow

The standard course workflow is:

```text
Microsoft Word source documents
            +
Course configuration (YAML)
            ↓
Generate the Quarto course scaffold
            ↓
Import and transform Word content
            ↓
Render the published course and handbook outputs
```

Word documents remain the editable content source. YAML defines the learning structure and navigation. Python import tools translate supported Word directives into Quarto-compatible components.

## Requirements

- Python 3.10 or later
- Quarto
- Pandoc
- Git
- TinyTeX when PDF output is required

Check the installed tools:

```bash
python3 --version
quarto --version
pandoc --version
```

Install TinyTeX if PDF publishing is required:

```bash
quarto install tinytex
```

## Installation

Clone the repository:

```bash
git clone https://github.com/cloudpedagogy/cloudpedagogy-learning-publisher.git
cd cloudpedagogy-learning-publisher
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it in Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Quick start

From the project root, run the following commands in order. Replace the configuration filename with the course being published.

```bash
PYTHONPATH=src python3 -m course_generator.cli build config/outbreak_ve_demo.yml
```

```bash
PYTHONPATH=src python3 -m course_generator.cli import-word config/outbreak_ve_demo.yml
```

```bash
PYTHONPATH=src python3 -m course_generator.cli render config/outbreak_ve_demo.yml
```

These commands:

1. Generate or update the Quarto scaffold and navigation.
2. Convert the configured Word documents and insert their content into the generated pages.
3. Render a new versioned publication under `output/courses/`.

Run `build` before `import-word`, and run `render` last. The final rendered version is the version created after the latest import.

## Course configuration

Course structure is defined in a YAML file under `config/`. The principal hierarchy is:

```text
module
└── sessions
    └── sections
        └── subpages
```

Each content page can reference a Word source:

```yaml
subpages:
  - id: OUTBREAK_VE_DEMO-se01-sec01-sp01
    title: "Outbreak Context"
    kind: text_page
    source_docx: "imports/courses/outbreak_ve_demo/docx/01_vaccine_effectiveness_outbreak.docx"
```

### Course-level standalone pages

Pages such as a glossary, references, help or accessibility information can appear at the same navigation level as the sessions:

```yaml
standalone_pages:
  - id: OUTBREAK_VE_DEMO-glossary
    title: "Glossary"
    kind: text_page
    source_docx: "imports/courses/outbreak_ve_demo/docx/course_glossary.docx"
```

Standalone pages use `templates/pages/standalone_page.qmd.j2`. The feature is generic and is not limited to glossaries.

## Word-first interactions

Authors can include supported directives as ordinary text in Word. During import, the directives are converted into Quarto or HTML components.

### Reveal

Reveal accepts paragraphs, lists, tables, equations, links and other Markdown-compatible content.

```text
Reveal
Label :: Show calculation
Calculate the risk in the vaccinated group.

Additional paragraphs and other content can appear here.
END Reveal
```

### Self-check

```text
SelfCheck
Question :: Why might vaccine effectiveness differ between populations?
Answer :: Differences in exposure and population structure can influence estimates.
END SelfCheck
```

The suggested answer is hidden until the learner opens it. Answers can contain multiple paragraphs, lists, tables and equations.

### Callout

```text
Callout :: important
Vaccine effectiveness measures the reduction in disease risk among vaccinated individuals compared with unvaccinated individuals.
END Callout
```

### Tabs

```text
Tabs
Tab :: Interpretation
Add paragraphs, lists, tables or equations here.
END Tab
Tab :: Limitations
Add the limitations here.
END Tab
END Tabs
```

### Quiz

```text
Quiz
Question :: What does vaccine effectiveness of 80% mean?
Option :: Vaccinated individuals have zero risk
Option :: Vaccinated individuals have an 80% lower risk than unvaccinated individuals
Answer :: Vaccinated individuals have an 80% lower risk than unvaccinated individuals
Explanation :: Vaccine effectiveness compares risk between the two groups.
END Quiz
```

Quiz explanations can contain multiple paragraphs, lists and equations.

### Other supported directives

- `R Code` with static or WebR modes
- `Image ::`
- `File ::`
- `YouTubeEmbed ::`
- `PanoptoEmbed ::`
- `HTML Embed ::`

Block directives should use their corresponding explicit end tags, such as `END Tabs`, `END Reveal`, `END SelfCheck`, `END Callout`, `END Quiz`, `END Image`, `END File`, `END HTML Embed` and `END R Code`.

Property lines belong to their surrounding block and do not need separate end tags. Examples include `Label ::`, `Question ::`, `Answer ::`, `Option ::`, `Explanation ::`, `Alt ::`, `Caption ::`, `Width ::`, `Echo ::` and `Output ::`.

## WebR

WebR enables R code to run in the learner's browser. Use the following within an `R Code` block:

```text
R Mode :: webr
```

When the importer detects WebR content, it checks the WebR extension and enables the required Quarto filter. Static R blocks continue to use `R Mode :: static`.

The WebR interface may add controls such as **View R History**, which lets learners review commands executed in interactive R cells.

## Standalone HTML interactions

Custom interactions and visualisations can be developed separately as HTML and embedded into Word-authored pages:

```text
HTML Embed :: resources/html/distribution_explorer.html
Title :: Distribution Explorer
Height :: 750
END HTML Embed
```

Self-contained HTML files are the most portable option because their JavaScript and supporting assets travel with the interaction. HTML that relies on a content delivery network requires an internet connection. Multi-file HTML applications require their supporting folders and relative paths to be preserved.

## Resources

Course resources can be organised by type:

```text
resources/
├── audio/
├── data/
├── docx/
├── html/
├── images/
├── misc/
├── pdf/
├── ppt/
└── video/
```

The Word importer copies referenced site resources into the generated course and rewrites paths relative to the target Quarto page.

## Project structure

```text
assemblies/     Publication assembly configuration
config/         Course YAML configuration
imports/        Editable source documents and converted intermediates
resources/      Shared course assets
src/            Python application code
templates/      Quarto and interaction templates
build/          Generated Quarto working projects
output/         Rendered publications and reports
tests/          Automated tests
tools/          Supporting utilities
```

Important implementation files include:

```text
src/course_generator/core/config_loader.py
src/course_generator/core/generator.py
src/course_generator/models/schema.py
src/course_generator/tools/import_word.py
templates/pages/standalone_page.qmd.j2
```

## Generated and source files

Treat `config/`, `src/`, `templates/`, reusable resources and intentional Word sources as maintainable project inputs. The `build/` and `output/` directories are generated and can normally be recreated.

Review `.gitignore` before committing large source documents, extracted media or generated output. Keep course source files in version control when they are required to reproduce a published course and their inclusion is permitted.

## Documentation

Additional operational and developer documentation can be maintained under `docs/`. Course-specific instructions should record:

- The configuration file used
- The source Word document locations
- Required Quarto extensions
- Resource dependencies
- The three publishing commands
- Any deployment or Moodle upload steps

## Licence

See [LICENSE](LICENSE) for licensing information.
