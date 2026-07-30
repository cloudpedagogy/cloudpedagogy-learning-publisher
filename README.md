# CloudPedagogy Learning Publisher

CloudPedagogy Learning Publisher is a Word-first publishing system for creating accessible, maintainable online learning with Quarto. Educators can author content in Microsoft Word while the system manages course structure, interaction conversion, navigation, resources and publication.

The Learning Publisher adds a structured course-production workflow on top of Quarto. Authors do not need to write Quarto Markdown directly for routine course development.

## Live demo

[Explore the Outbreak Investigation and Vaccine Effectiveness demo](https://cloudpedagogy-learning-publisher.s3.eu-west-2.amazonaws.com/outbreak_ve_demo/se01/OUTBREAK_VE_DEMO-se01-sec01-sp01.html)

The demo shows structured Word content published as an interactive Quarto learning page. It includes course navigation, rich content, self-checks, reveal activities, tabs, a quiz, browser-based R using WebR and an embedded Plotly visualisation.

## Core outputs

Depending on the course configuration, Learning Publisher can create:

- Multi-page Quarto learning websites
- Printable course HTML
- Individual lesson PDFs and combined PDF handbooks
- Interactive R activities using WebR
- Static R code examples and outputs
- Quizzes, self-checks, reveals, tabs and callouts
- Embedded images, files, videos and HTML interactions

Specialist Moodle utilities and Word-to-JavaScript renderers are maintained separately from the core Learning Publisher.

## Publishing workflow

```text
Microsoft Word source documents
            +
Course configuration (YAML)
            ↓
Generate the Quarto course scaffold
            ↓
Import and transform Word content
            ↓
Render the course website and configured page outputs
            ↓
Optionally assemble a combined handbook
```

The standard workflow renders the course website and any configured page
outputs. Combined handbooks are an optional post-processing step provided by
a separate publishing utility.

Word documents remain the editable content source. YAML defines the course hierarchy, page identifiers, titles, navigation and source-document paths. The Python importer translates supported Word directives into Quarto-compatible Markdown and HTML components.

## Requirements

- Python 3.10 or later
- Quarto
- Pandoc, normally provided through the Quarto installation
- Git
- TinyTeX when PDF output is required
- R and the required R packages when static R code is executed during rendering

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

When WebR content is detected, the importer checks for the trusted
`coatless/quarto-webr` extension, installs it when necessary and enables the
WebR filter. Internet access is required for the initial extension installation.

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

Install the Python dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Quick start

From the repository root, run the following commands in order. Replace the example configuration filename with the course you want to publish.

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

1. Generate or update the Quarto project, page scaffold and navigation.
2. Convert the configured Word documents and insert their content into the generated pages.
3. Render a versioned publication under `output/courses/`.

Run `build` before `import-word`, and run `render` after the latest import.

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

The optional [CloudPedagogy Word Course Splitter](https://github.com/cloudpedagogy/cloudpedagogy-word-course-splitter) can split a structured master Word document and generate Learning Publisher-compatible DOCX files and YAML paths.

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

Authors can add supported directives as ordinary text in Word. During import, the directives are converted into Quarto or HTML components.

### Reveal

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

The suggested answer remains hidden until the learner opens it. Answers can contain multiple paragraphs, lists, tables and equations.

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

## R content

An `R Code` block can use either a non-interactive static presentation or WebR:

```text
R Code
R Mode :: webr
Echo :: true
Output :: true
# Add R code here
END R Code
```

- `R Mode :: static` publishes a non-interactive R example.
- `R Mode :: webr` provides interactive R execution in the learner's browser.
- `Echo :: true` displays the code.
- `Echo :: false` hides the code.
- `Output :: true` displays the result when supported.
- `Output :: false` suppresses the result.

When the importer detects WebR content, it checks for the trusted
`coatless/quarto-webr` extension, installs it when necessary and enables the
required Quarto filter. The WebR interface may include controls such as **View
R History**, allowing learners to review commands executed in interactive
cells.

If a static R block is configured to execute during Quarto rendering, R and all
packages used by that block must be installed locally. Static blocks that only
display code do not require local execution.

## Standalone HTML interactions

Custom interactions and visualisations can be developed separately as HTML and embedded into Word-authored pages:

```text
HTML Embed :: resources/html/distribution_explorer.html
Title :: Distribution Explorer
Height :: 750
END HTML Embed
```

Self-contained HTML files are the most portable option because their JavaScript and supporting assets travel with the interaction. HTML that relies on a content delivery network requires an internet connection. Multi-file applications require their supporting folders and relative paths to remain intact.

Learning Publisher embeds these interactions; specialist renderer source code is maintained in its own repository rather than duplicated here.

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

For public demonstrations, use only resources and video links that are publicly accessible and that you have permission to publish. Institutionally restricted Panopto content should be replaced with an authorised public example or a placeholder.

## Handbook utilities

The retained publishing utilities include:

```text
src/course_generator/tools/
├── build_document_assembly.py
├── build_handbook_from_quarto.py
└── import_word.py
```

Use `build_handbook_from_quarto.py` to assemble course pages into a combined
printable handbook. Run the command with `--help` for the options available in
the installed version:

```bash
python3 src/course_generator/tools/build_handbook_from_quarto.py --help
```

## Project structure

```text
assemblies/     Publication assembly configuration
config/         Course YAML configuration
imports/        Editable source documents and converted intermediates
resources/      Shared course assets
src/            Python application code
templates/      Quarto and interaction templates
build/          Generated Quarto working projects
output/         Rendered course publications
tests/          Automated tests
src/course_generator/tools/
                Supporting publishing utilities
```

Important implementation files include:

```text
src/course_generator/core/config_loader.py
src/course_generator/core/generator.py
src/course_generator/interaction_resolver.py
src/course_generator/models/schema.py
src/course_generator/tools/import_word.py
templates/pages/standalone_page.qmd.j2
```

## Generated and source files

Treat `config/`, `src/`, `templates/`, reusable resources and intentional Word sources as maintainable project inputs. The `build/` and `output/` directories are generated and can normally be recreated.

Review `.gitignore` before committing large source documents, extracted media or generated output. Keep course source files in version control only when they are needed to reproduce a public course and you have permission to distribute them.

Python cache files are generated locally and should not be committed:

```gitignore
__pycache__/
*.py[cod]
```

## Companion projects

Related tools are maintained separately so that Learning Publisher remains focused:

- [CloudPedagogy Word Course Splitter](https://github.com/cloudpedagogy/cloudpedagogy-word-course-splitter)
- CloudPedagogy Moodle conversion and course-analysis tools
- CloudPedagogy Word-to-JavaScript visualisation renderers

## Documentation

Additional operational and developer documentation can be maintained under `docs/`. Course-specific instructions should record:

- The configuration file used
- The source Word document locations
- Required Quarto extensions
- Resource dependencies
- The publishing commands
- Handbook steps, when used
- Deployment or LMS upload steps

## Licence

See [LICENSE](LICENSE) for licensing information.
