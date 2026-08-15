# 

# Operating Handbook

## Authoring, Publishing and Maintaining Word-Based Interactive Learning Resources

# Handbook Overview

This handbook provides practical guidance for installing, configuring,
authoring, building and maintaining courses with Learning Publisher.

It is organised around the main stages of the publishing workflow:

1.  **About Learning Publisher** – introduces the purpose of Learning
    Publisher, its Word-first publishing model and the overall workflow.

2.  **Quick Start** – provides the shortest route from installation to
    generating and viewing a working Learning Publisher course.

3.  **Course Structure & Configuration** – explains project
    organisation, course configuration, sessions, pages, navigation and
```bash
source files.
```

4.  **Authoring in Word** – explains how to prepare structured Word
    content and use the supported Learning Publisher authoring
    components and directives.

5.  **R, WebR & Custom Interactions** – covers static R examples,
    browser-based R activities, external code files and custom
```text
HTML/JavaScript interactions.
```

6.  **Building & Publishing** – explains generation, Quarto rendering,
    previewing, output formats and deployment.

7.  **QA & Accessibility** – provides guidance for reviewing generated
    content, testing interactions and checking accessibility.

8.  **Reference & Troubleshooting** – provides command references,
    common problems and a systematic approach to diagnosing issues.

The handbook is intended to be used both as a **step-by-step guide for
new users** and as an **operational reference for experienced users**.

## About this handbook

This handbook explains how to use CloudPedagogy Learning Publisher to
create, maintain and publish interactive learning resources from
structured Microsoft Word documents.

It is intended primarily for:

- **Authors** preparing academic or learning content in Microsoft Word.

- **Operators** configuring courses, running Learning Publisher and
  checking publication outputs.

- **Developers** maintaining or extending the Learning Publisher
  software.

Most authors do not need to understand Python, Quarto or the internal
publishing architecture. They can work primarily in Word using familiar
document structures and the supported Learning Publisher directives.

Operators need a broader understanding of course configuration and the
publishing workflow. Developer-specific information is included only
where necessary for maintaining the platform.

The handbook is task-oriented. New users should begin with **Section 2:
Quick Start**. Later sections provide detailed guidance when creating
courses, using interactive features, troubleshooting or deploying
publications.

The current repository and its documented behaviour are the technical
authority for this handbook. Learning Publisher is under active
development, so documentation should be maintained alongside changes to
the software.

# 1. About Learning Publisher

## 1.1 What Learning Publisher does

CloudPedagogy Learning Publisher is a **Word-first publishing system for
creating accessible, maintainable online learning with Quarto**. Authors
work primarily in Microsoft Word, while a course-local YAML
configuration file defines the structure, navigation, source documents
and publication settings.

The basic model is:

```text
Microsoft Word
      +
course.yml
      +
code and resources
      │
      ▼
Learning Publisher
      │
      ▼
Generated Quarto project
      │
      ▼
Website + document outputs
```

Word remains the editable academic content source. Learning Publisher
converts supported Word content and directives into Quarto-compatible
content and generates the publication from it.

This means routine authors do **not** need to maintain Quarto Markdown
(.qmd) files directly.

If course content needs changing, the normal process is:

Edit the source

```text
↓
```

Run Learning Publisher

```text
↓
```

Check the regenerated publication

rather than manually editing the generated website.

## 1.2 What it can produce

Depending on the course configuration and source content, Learning
Publisher can produce:

- multi-page Quarto course websites;

- printable HTML;

- individual page outputs and combined Word/PDF handbooks;

- static R examples;

- browser-based WebR activities;

- self-checks, quizzes, reveals, tabs and callouts;

- images and downloadable resources;

- video and standalone HTML embeds;

- self-contained JavaScript interactions supplied as .js files.

The interactive website is normally the principal learner-facing
publication. Word and PDF handbooks provide static document
representations useful for purposes such as review, distribution and
archiving.

Some interactive website functionality necessarily has a different
representation in static document formats.

## 1.3 The core publishing workflow

Learning Publisher uses a defined publishing sequence:

Course source

```text
↓
Validate
↓
Build
↓
Import Word
↓
Build handbook
↓
Render
↓
```

Website and document outputs

The five principal stages are:

1.  **Validate** — checks the course YAML configuration.

2.  **Build** — creates or updates the generated Quarto project.

3.  **Import Word** — converts the configured Word sources and inserts
    the content into the generated pages.

4.  **Build handbook** — assembles the combined handbook source and
    configured document outputs.

5.  **Render** — publishes the course website.

This workflow is covered in detail later in the handbook. For routine
use, it is important to remember that **Build must precede Import
Word**.

## 1.4 Source versus generated content

Learning Publisher deliberately separates maintainable source from
generated publication files.

At course level, the maintained source normally consists of:

```text
imports/courses/my_course/
├── course.yml
├── docx/
├── code/
└── resources/
```

Learning Publisher uses these inputs to generate:

```text
build/courses/my_course/
```

and then the rendered publication under:

```text
output/courses/my_course/
```

The repository treats build/ and output/ as generated material that can
normally be recreated.

The practical rule is:

**Correct the source and regenerate the publication rather than manually
maintaining generated QMD or HTML.**

This preserves a reproducible relationship between the academic source
and the final learning resource.

# 2. Quick Start

This section provides the shortest complete route from a fresh Learning
Publisher installation to a working demonstration course.

More detailed configuration, authoring and publishing options are
covered in later sections.

## 2.1 Requirements

Learning Publisher currently requires:

- Python 3.10 or later; Python 3.13 is recommended for the current
  project;

- Quarto;

- Pandoc, normally supplied with Quarto;

- Git;

- TinyTeX when PDF output is required;

- R and the required R packages when static R code is executed during
  rendering.

Check the main tools:

```bash
python3.13 --version
quarto --version
pandoc --version
git --version
```

If python3.13 is unavailable but python3 is an appropriate supported
version, use:

```bash
python3 --version
```

and substitute python3 in the relevant setup command.

If PDF publishing is required, TinyTeX can be installed through Quarto:

```bash
quarto install tinytex
```

R is not required merely because a course contains browser-based WebR.
System R is required when **static R code is executed during
publication**.

## 2.2 Clone the repository

Clone the Learning Publisher repository:

```bash
git clone
https://github.com/cloudpedagogy/cloudpedagogy-learning-publisher.git
```

Enter the repository:

```bash
cd cloudpedagogy-learning-publisher
```

The repository is the maintained source for the Learning Publisher
application and also contains the demonstration course used in this
Quick Start.

## 2.3 Create the Python environment

On macOS or Linux, create a virtual environment:

```bash
python3.13 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

If the machine uses a suitable python3 rather than python3.13, use:

```bash
python3 -m venv .venv
```

On Windows PowerShell:

py -3.13 -m venv .venv

.venv\Scripts\Activate.ps1

Install Learning Publisher:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

The environment only needs to be created once. On subsequent sessions,
enter the repository and reactivate it:

```bash
source .venv/bin/activate
```

The Terminal prompt should normally begin with:

(.venv)

The package also defines a coursegen console entry point, but this
handbook uses the explicit python -m course_generator.cli form
consistently.

## 2.4 Check Learning Publisher

Confirm that the command-line application is available:

```bash
python -m course_generator.cli --help
```

For help with an individual command:

```bash
python -m course_generator.cli build --help
or:
python -m course_generator.cli render --help
```

For the handbook utility:

```bash
python src/course_generator/tools/build_handbook_from_quarto.py --help
```

## 2.5 Build the demonstration course

Learning Publisher includes the outbreak_ve_demo demonstration course
```yaml
under:
imports/courses/outbreak_ve_demo/
```

From the repository root, with .venv active, run the following commands
**in order**.

**1. Validate the course**
```bash
python -m course_generator.cli validate
imports/courses/outbreak_ve_demo/course.yml
```

This checks the course YAML configuration.

**2. Build the Quarto project**
```bash
python -m course_generator.cli build
imports/courses/outbreak_ve_demo/course.yml
```

This creates or updates the generated working project under:

```text
build/courses/outbreak_ve_demo/
```

**3. Import the Word content**
```bash
python -m course_generator.cli import-word
imports/courses/outbreak_ve_demo/course.yml
```

This converts the configured Word source and inserts it into the
generated course pages.

**4. Build the handbook**
```bash
python src/course_generator/tools/build_handbook_from_quarto.py
build/courses/outbreak_ve_demo
```

This assembles the combined handbook source and associated configured
document outputs.

**5. Render the website**
```bash
python -m course_generator.cli render
imports/courses/outbreak_ve_demo/course.yml --no-versioned
```

The website is rendered under:

```text
output/courses/outbreak_ve_demo/
```

On macOS, open it with:

```bash
open output/courses/outbreak_ve_demo/index.html
```

On other operating systems, open:

```text
output/courses/outbreak_ve_demo/index.html
```

in a browser. These commands and their ordering match the repository's
current documented Quick Start.

## 2.6 The five commands to remember

For routine publication, the core workflow can be reduced to:

validate

```text
↓
```

build

```text
↓
```

import-word

```text
↓
```

build handbook

```text
↓
```

render

For another course, replace outbreak_ve_demo with the appropriate course
name and YAML path.

For example:

```bash
python -m course_generator.cli validate
imports/courses/my_course/course.yml
python -m course_generator.cli build
imports/courses/my_course/course.yml
python -m course_generator.cli import-word
imports/courses/my_course/course.yml
python src/course_generator/tools/build_handbook_from_quarto.py
build/courses/my_course
python -m course_generator.cli render
imports/courses/my_course/course.yml --no-versioned
```

Use --no-versioned during routine testing when you want the same output
location to be replaced. Omit it when the renderer's default versioned
output behaviour is required.

## 2.7 When source content changes

You do not always need to repeat every setup step.

If a Word document or one of its referenced code files changes, rerun:

```text
Import Word
↓
Build handbook
↓
Render
```

If the course structure or course.yml changes, the safest workflow is:

```text
Validate
↓
Build
↓
Import Word
↓
Build handbook
↓
Render
```

When uncertain, running the complete five-stage pipeline is the safest
approach.

## 2.8 What successful publication looks like

A successful initial run should establish that:

- the YAML configuration validates;

- the Quarto working project is generated;

- Word content is imported;

- the handbook stage completes;

- the website renders;

- the generated website opens and its navigation and representative
  content can be checked.

Successful rendering is not the same as completing quality assurance.
Section 7 provides the full QA and troubleshooting procedure.

At this point, however, Learning Publisher is installed and operational.

The next step is to understand how a real course is organised. **Section
3: Course Structure and Configuration** explains the course folder,
course.yml, sessions, sections, pages, source-document paths and
navigation.

# 3. Course Structure and Configuration

Each Learning Publisher course is designed as a **self-contained
publishing project**. Its configuration, Word source, code and
supporting resources are kept together under imports/courses/.

A typical course has the following structure:

```text
imports/courses/my_course/
├── course.yml
├── docx/
├── code/
└── resources/
```

This course-local structure makes projects easier to move between
computers, run on a VM, version-control and reproduce without relying on
files elsewhere on a particular user's machine.

## 3.1 The course directory

Each course should have its own directory under:

```text
imports/courses/
```

For example:

```yaml
imports/courses/outbreak_ve_demo/
or:
imports/courses/my_course/
```

The directory name should be short, meaningful and stable. Avoid spaces
and unnecessary punctuation.

A more complete example is:

```text
imports/courses/my_course/
├── course.yml
├── docx/
│ ├── session01.docx
│ ├── session02.docx
│ └── glossary.docx
├── code/
│ ├── example.R
│ └── interaction.js
└── resources/
├── data/
├── html/
├── images/
├── pdf/
└── video/
```

Not every course requires every subdirectory. Create and use the folders
needed by the course.

The important principle is that files referenced by the course should
normally remain **inside the course directory**.

## 3.2 course.yml

The main configuration file is:

course.yml

For example:

```text
imports/courses/my_course/course.yml
```

This YAML file defines the structure Learning Publisher uses to generate
the Quarto publication.

It provides information such as:

- course/module metadata;

- sessions;

- sections;

- pages and subpages;

- source Word documents;

- navigation structure;

- page identifiers and output paths;

- relevant rendering and publication settings.

The current course-local model replaces older workflows that used a
separate top-level config/ directory. A course with its own course.yml
does not require a duplicate configuration file elsewhere.

## 3.3 YAML formatting

YAML is indentation-sensitive.

For example:

```yaml
module:
title: Example Course
code: EXAMPLE01
```

The spaces before title and code indicate that they belong to module.

Nested structures require further indentation:

```yaml
sessions:
```

\- id: session01

```yaml
title: Session 1
sections:
```

\- id: introduction

```yaml
title: Introduction
```

Use **spaces rather than tabs** for indentation.

A malformed YAML file can prevent Learning Publisher from understanding
the course structure, which is why validation should normally be the
first publishing command:

```bash
python -m course_generator.cli validate
imports/courses/my_course/course.yml
```

If validation fails, correct the configuration before continuing.

## 3.4 Course hierarchy

Learning Publisher supports a hierarchical course structure based around
sessions, sections and pages/subpages.

```yaml
Conceptually:
Course
│
├── Home
│
├── Session 1
│ ├── Section 1
│ ├── Section 2
│ └── Section 3
│
├── Session 2
│ ├── Section 1
│ └── Section 2
│
└── Glossary
```

This hierarchy is used to generate the course navigation.

The YAML structure should represent the **intended learner journey**,
rather than merely reproducing the filenames of the source documents.

A Word document is a source of content. The YAML configuration
determines where that content belongs in the published course.

## 3.5 Sessions

A session represents a major grouping of learning content.

For example:

```yaml
sessions:
```

\- id: session01

```yaml
title: Foundations of Outbreak Investigation
```

A second session might be:

\- id: session02

```yaml
title: Interpretation and Communication
```

The id should be stable and machine-friendly.

```yaml
Prefer:
```

session01

rather than:

Session 1!

The learner-facing wording belongs in title.

This separation allows a stable internal identifier to coexist with a
readable navigation label.

## 3.6 Sections

Sessions can contain sections representing the main parts of that
learning sequence.

```yaml
Conceptually:
sessions:
```

\- id: session01

```yaml
title: Foundations of Outbreak Investigation
sections:
```

\- id: outbreak-context

```yaml
title: Outbreak Context
```

\- id: measures-data

```yaml
title: Measures and Data
```

\- id: vaccine-effectiveness

```yaml
title: Calculating Vaccine Effectiveness
```

The resulting navigation can then appear conceptually as:

```yaml
SE01: Foundations of Outbreak Investigation
```

Section 1: Outbreak Context

Section 2: Measures and Data

Section 3: Calculating Vaccine Effectiveness

The precise labels displayed to learners depend on the configured course
structure and titles.

## 3.7 Pages and subpages

A section can contain one or more learning pages.

This is useful when a substantial topic should be divided into shorter
web pages rather than rendered as one very long page.

```yaml
Conceptually:
Section: Visualising Data
│
├── Introduction
├── Exploring Distributions
├── Comparing Groups
└── Interpreting Visualisations
```

This structure should be defined deliberately in the course
configuration.

A useful web page normally represents a coherent unit of learning rather
than an arbitrary number of Word pages.

When deciding whether material should become a separate page, consider:

- whether it has a clear learning purpose;

- whether it has a meaningful heading;

- whether the existing page is becoming excessively long;

- whether learners may need to return directly to that content;

- whether separating it improves navigation.

Do not split content simply to create more pages.

## 3.8 Word source documents

Pages reference the Word documents that provide their source content.

Word documents should normally be stored under:

```text
docx/
```

For example:

```yaml
docx/session01.docx
or:
docx/visualising-data.docx
```

The path in course.yml should be **relative to the course directory**.

This means a course can move from:

Mac

```yaml
to:
```

Linux VM

without rewriting absolute filesystem paths.

Avoid references such as:

/Users/name/Desktop/course/session01.docx

```yaml
or:
C:\Users\name\Documents\session01.docx
Use:
docx/session01.docx
```

instead.

## 3.9 One Word document can supply multiple pages

A course does not necessarily require one Word document for every
published web page.

A structured Word document can contain multiple sections that Learning
Publisher uses to create the configured publication structure.

This is useful when academic authors prefer to work with a larger
continuous document while the web publication requires shorter
learner-facing pages.

```yaml
Conceptually:
Word document
────────────────────────
```

Heading 1: Topic 3

Heading 2: Introduction

content...

Heading 2: Understanding the data

content...

Heading 2: Visualising distributions

content...

Heading 2: Comparing groups

content...

can support a publication structured as:

Topic 3

```text
├── Introduction
├── Understanding the data
├── Visualising distributions
└── Comparing groups
```

The exact split must correspond to the configured course structure and
supported importer behaviour.

This is one reason proper Word heading styles are important: headings
are structural information, not merely visual formatting.

Section 4 covers Word preparation in detail.

## 3.10 Pre-split Word sources

Courses can also use Word documents that have already been divided into
separate files.

For example:

```text
docx/
├── 01_outbreak_context.docx
├── 02_measures_and_data.docx
├── 03_calculating_vaccine_effectiveness.docx
└── 04_interpreting_results.docx
```

The YAML configuration can reference those documents appropriately.

Therefore Learning Publisher can support both:

one structured Word document

```yaml
↓
multiple published pages
and:
multiple Word documents
↓
configured course pages
```

The appropriate model depends on the way the source material is authored
and maintained.

The published navigation should be designed for learners rather than
being dictated by the number of source Word files.

## 3.11 Standalone pages

Some pages do not naturally belong inside a teaching session.

Typical examples include:

```text
Home
Glossary
Resources
```

About this course

These can be represented as standalone elements of the course structure
where supported by the configuration.

For example, the demonstration publication includes a glossary alongside
its principal learning sessions.

The principle is:

Use the hierarchy to represent the educational structure, not to force
every page into a session unnecessarily.

## 3.12 code/

Course-specific executable or source code should normally be stored
```yaml
under:
code/
```

For example:

```text
code/example.R
code/outbreak-risk-table.R
code/sir-model-interaction.js
```

A Word directive can then reference a course-relative file such as:

Source :: code/example.R

Keeping code external to the Word document is particularly useful for
substantial R or JavaScript examples because the code can be:

- tested independently;

- edited in an appropriate code editor;

- version controlled cleanly;

- reused without filling the Word source with lengthy program code.

Short examples may still be represented using supported authoring syntax
where appropriate.

## 3.13 resources/

Supporting publication files belong under:

```text
resources/
```

A useful organisation is:

```text
resources/
├── data/
├── html/
├── images/
├── pdf/
└── video/
```

Examples include:

```text
resources/data/patient-data.csv
resources/images/outbreak-chart.png
resources/html/custom-activity.html
resources/pdf/reference-guide.pdf
```

Again, use course-relative paths when referencing these files.

The directory structure can be extended where necessary, but it should
remain understandable and consistent.

Avoid turning resources/ into an unstructured collection of unrelated
files.

## 3.14 Keep resources inside the course

A course should not normally depend on:

```text
../../some-other-project/file.csv
```

or a personal directory elsewhere on the machine.

A self-contained course is easier to:

copy

version

archive

publish on another machine

run on a VM

hand to another operator

A useful test is:

If the entire my_course/ directory were copied to another valid Learning
Publisher installation, would its source files and local dependencies
still make sense?

Where practical, the answer should be yes.

## 3.15 File naming

Use predictable filenames.

```yaml
Prefer:
```

visualising-data.docx

outbreak-risk-table.R

blood-pressure.csv

distribution-example.png

Avoid unnecessarily complicated names such as:

Final version UPDATED 2 use this one!!.docx

Good filenames should be:

- meaningful;

- stable;

- reasonably short;

- free from unnecessary punctuation;

- consistent in case.

Using lowercase filenames with hyphens or underscores is a practical
convention for code and resources.

## 3.16 Filename case matters

Publishing may move between filesystems with different case-sensitivity
rules.

For example:

```yaml
resources/images/Chart.png
and:
resources/images/chart.png
```

may be treated as different files on a Linux system even if a local
development computer appears more forgiving.

The path in the source should therefore match the actual filename
exactly.

This is particularly important for:

images

R files

JavaScript

datasets

HTML resources

downloadable files

A case mismatch is a common explanation for content that works locally
but disappears after deployment to Linux or static hosting.

## 3.17 Validate before building

After creating or changing the course configuration, run:

```bash
python -m course_generator.cli validate
imports/courses/my_course/course.yml
```

Do this **before** attempting to diagnose later rendering problems.

If the YAML is invalid, there is little value in proceeding to
publication.

A useful workflow is:

Edit course.yml

```text
↓
Validate
↓
Build
↓
Import Word
↓
Render
```

Validation provides an early opportunity to catch configuration problems
before more expensive publishing stages are run.

## 3.18 Inspecting the configured course

Learning Publisher also provides an inspection command:

```bash
python -m course_generator.cli inspect
imports/courses/my_course/course.yml
```

This is useful when checking how the configuration is being interpreted.

Use it when you need to confirm the configured course structure before
rendering, particularly when working with a larger hierarchy of
sessions, sections and pages.

It is not required for every routine build.

## 3.19 Changing the navigation structure

If you change:

session structure

section structure

page structure

page order

course.yml source mapping

run the complete publishing sequence:

```bash
python -m course_generator.cli validate
imports/courses/my_course/course.yml
python -m course_generator.cli build
imports/courses/my_course/course.yml
python -m course_generator.cli import-word
imports/courses/my_course/course.yml
python src/course_generator/tools/build_handbook_from_quarto.py
build/courses/my_course
python -m course_generator.cli render
imports/courses/my_course/course.yml --no-versioned
```

This ensures that the generated Quarto structure is recreated before
Word content is imported.

By contrast, if only the text inside an existing Word source changes,
rebuilding the structural scaffold is not normally necessary.

## 3.20 Recommended course-configuration workflow

For a new course:

1. Decide the learner-facing structure

2. Create:

```text
imports/courses/my_course/
```

3. Add:

course.yml

4. Create:

```text
docx/
code/
resources/
```

as required

5. Add the Word source

6. Add local code and resources

7. Configure sessions, sections and pages

8. Validate course.yml

9. Inspect the structure if useful

10. Build and import the course

11. Review the generated navigation

12. Adjust the source/configuration if required

The key principle is to design the **course structure first**, rather
than allowing the accidental structure of existing files to dictate the
learner experience.

## 3.21 Course structure at a glance

| **Item** | **Purpose** | **Maintain directly?** |
|----|----|----|
| course.yml | Defines course structure and publication configuration | Yes |
| docx/ | Microsoft Word academic source | Yes |
| code/ | Course-specific R/JavaScript and similar code | Yes |
| resources/ | Images, data, HTML, PDFs and other assets | Yes |
| build/courses/<course>/ | Generated Quarto working project | Normally no |
| output/courses/<course>/ | Rendered publication | Normally no |

The most important distinction is:

```text
COURSE SOURCE
```

course.yml + docx + code + resources

```text
↓
```

Learning Publisher

```text
↓
GENERATED PUBLICATION
```

build + output

With the course structure established, the next task is preparing the
actual academic content. **Section 4: Authoring in Word** explains Word
heading structure, lists and tables, Learning Publisher
```text
metadata/directives, callouts, reveals, self-checks, tabs, quizzes,
media and the authoring practices required for reliable conversion.
```

# 4. Authoring in Word

Learning Publisher is designed around a **Word-first authoring model**.
Course authors create and maintain learning content in Microsoft Word,
while Learning Publisher converts that content into the structures
required by Quarto and the final published course.

This approach allows Word to remain the principal authoring and review
environment. Authors do not normally need to write Markdown, HTML or
Quarto syntax.

The Word documents are therefore not simply files to be converted. They
form the maintainable source content from which the published learning
materials are generated.

## 4.1 The Word-First Authoring Model

A typical workflow is:

Microsoft Word

```text
↓
```

Learning Publisher

```text
↓
```

Quarto source

```text
↓
```

Quarto rendering

```text
↓
```

Published learning materials

The Word source can contain:

- headings;

- paragraphs;

- lists;

- tables;

- images;

- links;

- mathematical content;

- learning activities;

- quizzes;

- self-check questions;

- callouts;

- reveal sections;

- R examples;

- executable WebR activities;

- embedded media;

- downloadable files.

Learning Publisher interprets both normal Word formatting and supported
authoring directives.

The resulting Quarto files should normally be regarded as **generated
output**, rather than the primary location for editing course content.

Where possible, changes should therefore be made in the Word source and
the course rebuilt.

## 4.2 One Word Document per Page

The standard Learning Publisher model uses a separate Word document for
each course page.

For example:

```bash
source/
├── introduction.docx
├── epidemiological-measures.docx
├── study-design.docx
├── visualising-data.docx
└── summary.docx
```

These files are referenced from the course configuration.

```yaml
Conceptually:
sessions:
```

\- title: "Introduction"

```yaml
pages:
```

\- title: "Introduction to the module"

```bash
source: "source/introduction.docx"
```

\- title: "Epidemiological measures"

```bash
source: "source/epidemiological-measures.docx"
```

Separating pages in this way makes the relationship between source
material and published pages explicit.

It also makes individual pages easier to:

- review;

- replace;

- version;

- troubleshoot;

- regenerate.

## 4.3 Heading Structure

Word heading styles are important because they communicate document
structure to Learning Publisher.

Authors should use actual Word heading styles rather than manually
formatting text to look like headings.

For example:

Heading 1

Heading 2

Heading 3

should be created using Word's built-in styles.

Avoid creating headings by simply:

- increasing the font size;

- making text bold;

- changing its colour;

- typing headings as ordinary paragraphs.

Semantic heading styles provide a more reliable source structure and
improve the accessibility of both the source and generated content.

## 4.4 Page Titles and Heading Levels

The course configuration determines the overall course navigation and
page titles.

Within an individual Word source document, headings should therefore
represent the structure **within that page**.

A typical page might contain:

Visualising data

Why visualisation matters

Choosing an appropriate chart

Bar charts

Line charts

Common mistakes

Summary

The page title may be supplied through the course configuration, while
the internal sections use appropriate Word heading levels.

Authors should maintain a logical hierarchy and avoid skipping heading
levels unnecessarily.

For example:

Heading 2

Heading 3

Heading 3

Heading 2

Heading 3

is preferable to:

Heading 2

Heading 4

Heading 2

## 4.5 Paragraphs and Ordinary Text

Normal prose should use Word's standard paragraph style.

Authors can continue to use familiar Word features such as:

- bold;

- italics;

- numbered lists;

- bulleted lists;

- hyperlinks;

- tables.

The aim is to allow academic authors to work in a conventional document
environment while keeping the document sufficiently structured for
reliable transformation.

Excessive manual formatting should be avoided.

The semantic structure of the document is more important than its
precise appearance in Word because the final presentation is controlled
by the publishing system.

## 4.6 Lists

Standard Word bulleted and numbered lists can be used.

For example:

The main advantages are:

• reproducible publishing;

• maintainable source documents;

• consistent formatting;

• multiple output formats.

Numbered procedures can similarly be written as ordinary Word numbered
```yaml
lists:
```

1. Prepare the Word document.

2. Add the document to the course configuration.

3. Generate the Quarto source.

4. Render the course.

5. Review the output.

Nested lists should use Word's normal list-level controls rather than
manually inserted spaces or symbols.

## 4.7 Tables

Tables should be created using Word's table functionality.

Keep tables structurally simple where possible.

For accessibility, tables should:

- contain meaningful column headings;

- avoid unnecessary merged cells;

- avoid using tables purely for visual layout;

- remain understandable when read sequentially.

A simple source table might contain:

| **Measure** | **Description**                             |
|-------------|---------------------------------------------|
| Incidence   | New cases occurring during a defined period |
| Prevalence  | Existing cases within a population          |
| Mortality   | Deaths occurring within a population        |

Learning Publisher converts supported Word tables into the corresponding
published representation.

## 4.8 Images

Images can be included within the Word source.

Images intended to communicate information should have meaningful
alternative text.

Decorative images should be identified appropriately where the authoring
workflow supports this.

Good alternative text describes the purpose or information conveyed by
the image rather than merely stating that an image exists.

For example:

```yaml
Poor:
```

Graph

```yaml
Better:
```

Line graph showing incidence increasing from approximately

20 to 65 cases per 100,000 between 2010 and 2020.

Alternative text should be considered part of the academic content and
reviewed alongside the surrounding text.

## 4.9 Hyperlinks

Normal Word hyperlinks can be used for external resources.

Link text should describe the destination or purpose of the link.

```yaml
Prefer:
```

Read the WHO guidance on outbreak investigation.

rather than:

Click here.

Descriptive links improve accessibility and make the content easier to
understand when links are encountered outside their surrounding visual
context.

## 4.10 Learning Publisher Directives

Learning Publisher extends ordinary Word authoring through structured
directives.

Directives allow an author to request richer learning components without
writing the underlying HTML, JavaScript or Quarto implementation.

Conceptually, the author specifies:

component type

```text
↓
```

component options/content

```text
↓
```

Learning Publisher transformation

```text
↓
```

interactive or styled output

Supported components include features such as:

- tabs;

- R examples;

- WebR activities;

- reveal content;

- self-check activities;

- callouts;

- quizzes;

- images and files;

- YouTube and Panopto media;

- mathematical content;

- custom interactive material.

The precise syntax should follow the conventions implemented by the
current Learning Publisher version.

## 4.11 Tabs

Tabs can be used where several closely related pieces of information are
better presented within the same part of a page.

For example, an activity might provide separate views for:

Explanation

Example

R code

which Learning Publisher can render as a tabbed interface.

Tabs should be used selectively. Important content should not be hidden
unnecessarily simply to reduce the apparent length of a page.

## 4.12 Reveal Content

Reveal components allow information to remain hidden until the learner
chooses to display it.

A common educational pattern is:

Question

\[Reveal answer\]

Explanation

This is useful where learners should consider a question before seeing
the answer.

Typical uses include:

- model answers;

- explanations;

- hints;

- worked solutions;

- additional information.

Reveal components should not contain information that learners must see
without interaction.

## 4.13 Self-Check Activities

Self-check components can be used to encourage learners to pause and
assess their understanding.

A typical pattern is:

Consider the following question.

\[learner considers response\]

Reveal feedback

These activities are intended primarily for formative learning rather
than formal assessment.

They can be combined with explanations and feedback so that learners
understand why a particular response is appropriate.

## 4.14 Callouts

Callouts provide visually distinct blocks for information that requires
particular emphasis.

Typical uses include:

- notes;

- warnings;

- important information;

- examples;

- tips.

For example:

IMPORTANT

Incidence and prevalence measure different aspects of disease

frequency and should not be used interchangeably.

Learning Publisher converts the source representation into the
appropriate Quarto callout structure.

Callouts should communicate a genuine semantic purpose rather than being
used solely for decoration.

## 4.15 Quizzes

Learning Publisher can generate quiz-style interactions from structured
```bash
source content.
```

A quiz component may contain:

- a question;

- answer options;

- the correct response;

- feedback;

- explanatory material.

For example, conceptually:

```yaml
Question:
```

Which measure describes new cases occurring during a defined period?

A. Prevalence

B. Incidence

C. Case fatality

D. Mortality

Correct answer:

B

```yaml
Feedback:
```

Incidence measures the occurrence of new cases within a defined

population over a specified period.

The author concentrates on the educational content while Learning
Publisher generates the required presentation and interaction.

Quiz content should be checked carefully after rendering to ensure that:

- all options appear;

- the correct answer is recognised;

- feedback is displayed appropriately;

- keyboard operation works;

- the interaction remains understandable without relying solely on
  colour.

## 4.16 R Code

Learning Publisher supports the inclusion of R code in learning
materials.

R code may be presented simply as an example for learners to read or may
form part of an executable WebR activity.

For maintainability, substantial R examples should normally be stored as
external .R files rather than repeatedly embedded directly in Word.

For example:

```text
code/
├── incidence_example.R
├── prevalence_example.R
└── visualisation_example.R
```

A Word document can then reference the appropriate source file.

```yaml
Conceptually:
```

Source :: code/visualisation_example.R

This separates executable code from the prose while allowing the Word
document to determine where the example appears in the learning
sequence.

The approach also makes the R code easier to:

- test;

- review;

- reuse;

- version;

- maintain.

## 4.17 Static R Examples

Not every R example needs to be executable.

Static examples are appropriate when the purpose is to:

- demonstrate syntax;

- explain a programming concept;

- show a completed solution;

- discuss a particular function;

- illustrate good coding practice.

For example:

```r
library(tidyverse)
```

cases \|\>

```r
ggplot(aes(x = week, y = incidence)) +
geom_line()
```

The generated course can present the code using syntax highlighting
without requiring the learner to execute it.

## 4.18 WebR Activities

WebR allows R code to execute within the learner's browser.

This enables Learning Publisher to provide interactive R activities
without requiring the learner to install R locally or connect to a
conventional R server.

```yaml
Conceptually:
```

Word learning activity

```text
↓
```

R source

```text
↓
```

Learning Publisher

```text
↓
```

WebR-enabled page

```text
↓
```

R executes in the browser

A WebR activity can therefore allow learners to:

- inspect code;

- modify code;

- execute code;

- view results;

- experiment with examples.

Because the computation occurs in the browser, a generated WebR page can
also support local use once the required assets are available.

WebR activities should always be tested in the final rendered output
rather than assuming that valid R code will automatically produce an
appropriate browser-based learning activity.

## 4.19 Independent Coding Activities

Where learners are expected to write or modify code independently, the
activity should make the distinction between demonstration and learner
work clear.

For example:

Worked example

\[example code\]

Your task

Modify the code so that the graph displays incidence by age group.

\[editable coding environment\]

The instructions should specify:

- what the learner is expected to change;

- what output they should produce;

- what data or objects are available;

- whether a model solution is provided.

This makes the activity pedagogically clearer than simply presenting an
editable code block without explanation.

## 4.20 External Files and Resources

Learning pages can reference supporting resources stored within the
project.

For example:

```text
resources/
├── outbreak_data.csv
├── study_design.pdf
└── exercise_template.docx
```

These resources can then be made available from the generated course as
downloadable files or used by other components.

Relative project paths should be preferred where possible.

For example:

```text
resources/outbreak_data.csv
```

is more portable than a machine-specific path such as:

/Users/example/Documents/course/resources/outbreak_data.csv

Absolute local paths should not be embedded in course content because
they will normally fail when the project is moved to another computer or
server.

## 4.21 YouTube

YouTube material can be incorporated into course pages using the
supported Learning Publisher media mechanism.

Authors should provide the appropriate video reference rather than
manually constructing iframe HTML.

The publisher can then generate the required embed structure
consistently.

Authors should also consider:

- captions;

- transcripts;

- meaningful surrounding context;

- alternatives where the external media cannot be accessed.

A video should normally be introduced in the learning content rather
than appearing without explanation.

## 4.22 Panopto

Learning Publisher can also support Panopto content.

This is particularly useful in institutional environments where teaching
videos are hosted through Panopto rather than public video services.

As with other external media, authors should avoid manually inserting
complex embed code where a supported Learning Publisher mechanism
exists.

The source should contain the information necessary for the publisher to
construct the appropriate output.

Institutional permissions remain important. Learning Publisher can
generate the link or embed, but it cannot make a restricted Panopto
recording accessible to a learner who does not have permission to view
it.

## 4.23 Mathematical Content

Mathematical expressions can be included in learning content and
converted into suitable web representations.

Where mathematical material is used, the generated page should be
checked for both visual presentation and accessibility.

Learning Publisher's output pipeline can support MathML as part of
producing accessible mathematical content.

Authors should use genuine mathematical structures rather than inserting
screenshots of equations wherever practical.

Text or mathematical markup is generally preferable to an image because
it can be:

- resized;

- searched;

- copied;

- interpreted by appropriate assistive technologies.

## 4.24 Custom HTML and JavaScript Interactions

Learning Publisher can accommodate custom interactive material where the
standard components are insufficient.

For example, a course might contain a purpose-built JavaScript
interaction stored within the project.

```yaml
Conceptually:
interactions/
└── risk-calculator/
├── index.html
├── script.js
└── style.css
```

The Word source can determine where that interaction should appear.

Custom interactions should be treated as more advanced components
because they introduce additional requirements for:

- testing;

- accessibility;

- browser compatibility;

- maintenance;

- security review.

Where a standard Learning Publisher component can achieve the same
educational objective, the standard component will generally be easier
to maintain.

## 4.25 Authoring for Accessibility

Accessibility should begin in the Word source rather than being treated
solely as a correction applied after publishing.

Authors should therefore:

- use genuine heading styles;

- maintain a logical heading hierarchy;

- provide alternative text for meaningful images;

- use descriptive link text;

- provide meaningful table headings;

- avoid communicating information through colour alone;

- provide context for multimedia;

- avoid unnecessary visual complexity;

- write clear instructions for interactive activities.

Generated content should still be tested after rendering because
accessible source material does not guarantee that every generated
interaction will behave correctly.

## 4.26 Authoring for Maintainability

The source should be written with future maintenance in mind.

```yaml
Prefer:
```

Word source

+

external R files

+

project resources

+

course configuration

over large amounts of manually embedded HTML or duplicated technical
content.

A useful principle is:

Keep academic content in the most maintainable authoring format and keep
technical implementation in the publishing system.

For most pages, this means the academic author works primarily in Word
while Learning Publisher manages the technical transformation.

## 4.27 What Authors Should Not Normally Edit

After conversion, Learning Publisher generates Quarto source files and
supporting assets.

These generated files can technically be edited, but doing so creates a
risk that changes will be lost the next time the course is generated.

The preferred workflow is therefore:

Edit Word

```text
↓
```

Regenerate

```text
↓
Render
↓
```

Review

rather than:

Edit Word

```text
↓
```

Generate Quarto

```text
↓
```

Manually edit generated Quarto

```text
↓
```

Regenerate

```text
↓
```

Lose manual changes

Where a change genuinely requires modifications to the generated
behaviour, it should normally be implemented in the Learning Publisher
templates, transformation code, configuration or supported extension
mechanism rather than repeatedly patched into generated pages.

## 4.28 Reviewing the Generated Page

Authors should review the rendered HTML rather than relying entirely on
the appearance of the Word source.

The final HTML represents what the learner will actually experience.

For each page, check:

- headings and page structure;

- paragraphs and lists;

- tables;

- images and alternative text;

- hyperlinks;

- callouts;

- reveal components;

- quizzes;

- self-check activities;

- R code;

- WebR execution;

- videos;

- downloadable resources;

- mathematical content;

- keyboard operation;

- responsive behaviour where relevant.

This distinction is important:

```r
Word = authoring and review source
HTML = learner-facing implementation
```

Both should be reviewed, but for different purposes.

## 4.29 Recommended Authoring Workflow

A practical workflow for developing a new page is:

1. Create the Word document.

2. Apply appropriate Word heading styles.

3. Write the learning content.

4. Add images, tables and links.

5. Add Learning Publisher components where required.

6. Store substantial R code in external .R files.

7. Add supporting files to the project resources.

8. Reference the Word document from the course YAML.

9. Run Learning Publisher.

10. Render the Quarto course.

11. Open the generated HTML.

12. Review the page as a learner would experience it.

13. Correct the Word source or supporting files.

14. Regenerate and render.

15. Repeat until the page passes content and technical review.

This maintains a clear separation between **authoring**, **generation**
and **publication**.

## 4.30 Authoring Principle

The central authoring principle of Learning Publisher is:

Author in Word.

Structure explicitly.

Keep code and resources maintainable.

Generate reproducibly.

Review the published output.

This allows Microsoft Word to remain a practical academic authoring and
review environment while Learning Publisher handles the transformation
into structured digital learning materials.

# 5. R, WebR & Custom Interactions

Learning Publisher supports code-based and custom interactive learning
materials alongside standard Word-authored content.

The main supported approaches are:

- static R examples;

- executable R activities using WebR;

- external R source files;

- custom HTML and JavaScript interactions;

- supporting files and resources.

Where possible, code should be kept outside the Word document and
referenced from the source material. This makes code easier to test,
maintain and reuse.

## 5.1 Static R Code

R code can be included as a non-executable example where learners need
to read or study code without running it.

For example:

```r
library(tidyverse)
```

cases \|\>

```r
ggplot(aes(x = week, y = incidence)) +
geom_line()
```

Static code is appropriate for:

- demonstrating syntax;

- explaining functions;

- showing worked examples;

- presenting model solutions;

- discussing coding conventions.

Learning Publisher renders the code as a formatted code block with
syntax highlighting.

## 5.2 External R Files

For maintainability, R code should normally be stored in external .R
files rather than copied directly into Word.

A project might contain:

```text
code/
├── incidence.R
├── prevalence.R
└── visualisation.R
```

The Word source can reference the required file using the supported
```bash
source syntax:
```

Source :: code/visualisation.R

Learning Publisher reads the referenced file and inserts the code into
the generated learning material.

This approach has several advantages:

- R code can be tested independently;

- the same code can be reused;

- Word documents remain readable;

- code can be version controlled cleanly;

- coding errors are easier to identify;

- changes do not require copying code between documents.

Relative paths should be used so that the project remains portable
between computers and publishing environments.

## 5.3 WebR

Learning Publisher supports executable R activities through WebR.

WebR allows R to run within a web browser using WebAssembly. This means
that learners can interact with R without requiring a conventional local
R installation or a remote R execution server.

The general workflow is:

Word activity

```text
↓
```

Referenced R source

```text
↓
```

Learning Publisher

```text
↓
```

Quarto page

```text
↓
```

WebR environment

```text
↓
```

R executes in the learner's browser

This makes it possible to incorporate executable coding activities
directly into a published course.

## 5.4 WebR Activities

A WebR activity can allow learners to:

- view R code;

- execute code;

- modify code;

- rerun an example;

- inspect output;

- experiment with different values.

A typical learning sequence might be:

Worked example

```text
↓
```

Explanation

```text
↓
```

Executable R code

```text
↓
```

Learner modifies code

```text
↓
```

Learner runs revised code

```text
↓
```

Output displayed in the page

WebR should be used where execution contributes meaningfully to the
learning activity. A static code example is usually sufficient where
learners only need to inspect code.

## 5.5 Worked Examples and Independent Tasks

Coding activities should distinguish clearly between code that
demonstrates a technique and code that the learner is expected to
modify.

For example:

Worked example

The following code creates a line graph of incidence by week.

\[example R code\]

Your task

Modify the code so that the graph displays incidence by age group.

\[editable R activity\]

Instructions should make clear:

- what the learner should change;

- what result is expected;

- which objects or datasets are available;

- whether they should modify existing code or write their own;

- whether a solution is available.

This avoids presenting an executable code editor without a clear
learning purpose.

## 5.6 Designing R Activities

R activities should follow the same principles as the rest of the
learning material.

Prefer short, focused examples over unnecessarily large scripts.

Where a longer analysis is required, divide it into meaningful stages.

For example:

1. Load the data

2. Inspect the variables

3. Transform the data

4. Create the visualisation

5. Interpret the result

This makes both the R code and the learning sequence easier to
understand.

Code should also follow consistent conventions. Where appropriate,
examples should use a consistent contemporary R style throughout a
course rather than switching unnecessarily between different syntactic
approaches.

## 5.7 Testing WebR

Executable R should always be tested in the generated HTML.

Valid R code alone does not guarantee that the activity will work
correctly in WebR.

Check that:

- the WebR environment loads;

- the expected packages are available;

- required data files can be accessed;

- the initial code is displayed correctly;

- code can be edited where intended;

- code executes successfully;

- output appears correctly;

- errors are understandable;

- the activity can be operated using a keyboard;

- instructions remain understandable independently of the interface.

Testing should be performed using the same generated output that
learners will receive.

## 5.8 Browser-Based Execution

A major characteristic of WebR is that R executes in the browser.

```yaml
Conceptually:
```

Traditional server model

```text
Browser
↓
Server
↓
R
↓
Server
↓
Browser
```

WebR model

```text
Browser
↓
WebR
↓
```

R execution

This reduces the need for server-side computational infrastructure for
suitable learning activities.

However, browser execution also means that activities should be designed
with the constraints of the browser environment in mind.

Large datasets, complex dependencies or computationally expensive
analyses may not be appropriate for WebR-based activities.

## 5.9 Local and Offline Use

Generated learning materials can be viewed locally, and browser-based
execution can support learning activities without a conventional R
installation.

Whether a particular WebR activity works completely offline depends on
whether all required WebR assets, packages, datasets and other
dependencies are available to the local course.

Therefore, offline behaviour should be tested explicitly where offline
delivery is required.

Do not assume that an activity is fully offline-compatible simply
because R executes in the browser.

## 5.10 Supporting Data and Resources

R activities may require datasets or other supporting files.

These should be stored within the project in a predictable location.

For example:

```text
resources/
├── data/
│ ├── outbreak.csv
│ └── population.csv
└── documents/
└── exercise-instructions.pdf
```

Code should use project-relative references wherever possible.

This should be preferred:

```text
resources/data/outbreak.csv
```

over a machine-specific path such as:

/Users/name/Documents/project/outbreak.csv

Machine-specific paths make the project difficult to move between local
computers, virtual machines and publishing environments.

## 5.11 Custom HTML and JavaScript

Learning Publisher can also incorporate custom HTML and JavaScript where
an activity cannot reasonably be implemented using the standard
components.

Examples might include:

- interactive diagrams;

- simulations;

- specialist calculators;

- bespoke data visualisations;

- interactive decision activities.

A project might contain:

```text
interactions/
└── risk-calculator/
├── index.html
├── script.js
└── style.css
```

The interaction can then be referenced from the learning content using
the mechanism supported by Learning Publisher.

Keeping the interaction in its own directory makes its dependencies
easier to identify and maintain.

## 5.12 When to Use a Custom Interaction

Custom HTML or JavaScript should not be the default approach.

Use a standard Learning Publisher component where one already meets the
educational requirement.

For example, use the standard:

- quiz component for a conventional quiz;

- reveal component for hidden feedback;

- self-check component for a simple formative activity;

- tab component for related content views.

A custom interaction is more appropriate when the learning design
genuinely requires behaviour that the standard components cannot
provide.

This distinction helps keep courses maintainable.

## 5.13 Maintaining Custom Interactions

Custom interactions introduce additional technical responsibilities.

They should therefore be:

- stored as project files rather than embedded as large blocks inside
  Word;

- version controlled;

- documented where their behaviour is not obvious;

- tested independently;

- tested again after integration into the course.

Where external libraries are required, their use should also be
documented so that the interaction can be reproduced in another
environment.

## 5.14 Accessibility of Interactive Content

Interactive activities require accessibility testing in addition to
ordinary content review.

Check that:

- controls have meaningful labels;

- keyboard users can operate the activity;

- keyboard focus remains visible;

- instructions do not depend solely on visual positioning;

- colour is not the only means of communicating information;

- feedback is understandable;

- interactive states are communicated appropriately;

- important content remains available to users who cannot operate the
  interaction as originally envisaged.

Custom JavaScript components require particular attention because
Learning Publisher cannot automatically guarantee the accessibility of
arbitrary custom code.

## 5.15 Choosing the Appropriate Approach

The simplest component that meets the learning objective should normally
be used.

A useful decision model is:

Does the learner only need to read the code?

\|

Yes

```text
↓
```

Static R example

Does the learner need to execute or modify R?

\|

Yes

```text
↓
```

WebR activity

Can a standard Learning Publisher component

provide the required interaction?

\|

Yes

```text
↓
```

Use the standard component

Is genuinely custom behaviour required?

\|

Yes

```text
↓
```

Custom HTML / JavaScript

This avoids introducing unnecessary technical complexity into course
materials.

## 5.16 Recommended Project Structure

A course containing code and interactive resources might use a structure
such as:

```text
project/
├── config/
│ └── course.yml
│
├── source/
│ ├── introduction.docx
│ ├── visualising-data.docx
│ └── exercise.docx
│
├── code/
│ ├── example.R
│ └── exercise.R
│
├── resources/
│ └── data/
│ └── outbreak.csv
│
├── interactions/
│ └── risk-calculator/
│ ├── index.html
│ ├── script.js
│ └── style.css
│
└── output/
```

The exact structure of an existing Learning Publisher project should be
retained where it differs from this illustrative example.

The important principle is separation of concerns:

```text
Word → learning content
YAML → course structure and configuration
R files → R code
Resources → data and supporting files
Interactions → custom interactive components
Generated → publishing output
```

## 5.17 Editing and Regeneration

As with ordinary course content, generated R and interaction output
should not normally become the primary editing source.

```yaml
Instead:
```

Edit Word / R / interaction source

```text
↓
```

Run Learning Publisher

```text
↓
```

Render course

```text
↓
```

Review HTML

This preserves the reproducibility of the project.

If a problem repeatedly requires manual modification of generated HTML,
it is usually better to correct the relevant source, template or
Learning Publisher transformation.

## 5.18 Future Code Environments

The code integration model is designed so that additional programming
environments can be incorporated without changing the fundamental
Word-first publishing workflow.

The core pattern remains:

Word learning content

+

external code/resources

```text
↓
```

Learning Publisher

```text
↓
```

learner-facing course

Only environments that are actually implemented and tested should be
treated as supported functionality.

This keeps the authoring model extensible while ensuring that the
handbook describes the capabilities of the current Learning Publisher
release accurately.

Section 6 should now cover the operational pipeline: generating the
course, rendering it, previewing it, and understanding the resulting
outputs. I'll keep it streamlined so that detailed error diagnosis can
remain in Section 8.

# 6. Building & Publishing

Once the course configuration, Word source documents and supporting
resources are ready, Learning Publisher can generate the Quarto project
and render the final learning materials.

The standard workflow is:

Word + YAML + resources

```text
↓
```

Learning Publisher

```text
↓
```

Generated Quarto project

```text
↓
```

Quarto render

```text
↓
```

HTML course

The generated Quarto files should normally be treated as build output.
Changes to course content should be made in the Word source,
configuration or supporting files and then regenerated.

## 6.1 Activate the Python Environment

Before running Learning Publisher, activate the project's Python virtual
environment.

On macOS or Linux:

```bash
source .venv/bin/activate
```

If the environment has not yet been created:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Once activated, the shell prompt will normally indicate that the virtual
environment is in use.

For example:

(.venv) user@computer learning-publisher %

The environment only needs to be created once. It should be activated
again whenever a new terminal session is used to run the Python tools.

## 6.2 Check Quarto

Learning Publisher generates a Quarto project, so Quarto must be
available when the course is rendered.

Check the installation with:

```bash
quarto --version
```

If Quarto returns a version number, it is available from the current
command line.

You can also check Python:

```bash
python --version
```

or, depending on the environment:

```bash
python3 --version
```

## 6.3 Run from the Project Root

Commands should normally be run from the root of the Learning Publisher
repository.

For example:

```bash
cd cloudpedagogy-learning-publisher
```

You should then be able to see the main project directories and files.

A simplified project structure might resemble:

```text
cloudpedagogy-learning-publisher/
├── config/
├── docs/
├── src/
├── requirements.txt
└── ...
```

Running commands from a predictable location avoids problems with
relative paths to configuration files, Word documents, code and
resources.

## 6.4 Generate the Course

The course configuration provides Learning Publisher with the
information required to assemble the course.

Conceptually, the command follows the pattern:

```bash
python \<publisher-script\> \<course-config\>
```

For example:

```bash
python src/\<publisher-script\>.py config/<course>.yml
```

Use the actual script and configuration filenames provided by the
current repository.

The generation stage reads the course configuration and associated Word
```bash
source files, then creates the corresponding Quarto source and
supporting files.
```

The process is:

course.yml

+

Word documents

+

resources

```text
↓
```

Learning Publisher

```text
↓
```

Quarto source

Any errors reported during this stage should be resolved before
proceeding to publication.

## 6.5 Generated Quarto Project

The generated project contains the files required by Quarto to construct
the learner-facing course.

Depending on the configuration and features used, this may include:

- .qmd pages;

- Quarto configuration;

- navigation definitions;

- images;

- stylesheets;

- JavaScript;

- R resources;

- WebR components;

- downloadable resources;

- other supporting assets.

These files form the intermediate publishing layer between the
maintainable source and the final course.

The relationship is:

Maintainable source

Word / YAML / code / resources

```text
↓
```

Learning Publisher

```text
↓
```

Generated Quarto

```text
↓
```

Quarto

```text
↓
```

Published output

## 6.6 Do Not Normally Edit Generated Files

Generated .qmd, HTML or supporting files should not normally be edited
directly.

For example, avoid this workflow:

Word

```text
↓
```

Generate

```text
↓
```

Manually edit .qmd

```text
↓
Render
```

The course may initially appear correct, but the manual changes can be
lost the next time Learning Publisher regenerates the project.

```yaml
Instead:
```

Edit source

```text
↓
```

Generate

```text
↓
Render
↓
```

Review

If the same manual correction is repeatedly required, the underlying
```bash
source, configuration, template or transformation should normally be
corrected.
```

## 6.7 Render the Course

Once the Quarto source has been generated, render the project with
Quarto.

From the generated Quarto project directory:

```bash
quarto render
```

Quarto processes the project and creates the published output.

For a website, the resulting files commonly include:

\_site/

```text
├── index.html
├── ...
├── site_libs/
└── supporting assets
```

The exact output structure depends on the Quarto configuration generated
by Learning Publisher.

## 6.8 Preview the Course

During development, Quarto's preview server is usually the most
convenient way to inspect the course.

```bash
Run:
quarto preview
```

Quarto will start a local web server and provide a local address that
can be opened in a browser.

This allows you to review the course in an environment closer to normal
web delivery than opening individual files directly.

Preview mode is particularly useful while checking:

- navigation;

- internal links;

- images;

- styling;

- quizzes;

- reveal components;

- WebR;

- JavaScript interactions;

- downloadable resources.

Stop the preview server with:

Ctrl+C

## 6.9 Opening Rendered HTML Locally

Rendered HTML can also be inspected locally.

For simple static pages, opening the generated HTML file directly may be
sufficient.

However, some browser functionality behaves differently when pages are
opened through a file:// path rather than served through a web server.

For that reason, when testing interactive content, prefer:

```bash
quarto preview
```

or another local web server.

The environment used for testing should reflect the intended learner
environment as closely as practical.

## 6.10 The Standard Build Cycle

During course development, the normal cycle is:

1. Edit Word/YAML/resources

```text
↓
```

2. Generate Quarto

```text
↓
```

3. Render or preview

```text
↓
```

4. Review in browser

```text
↓
```

5. Correct source

```text
↓
```

6. Regenerate

This cycle can be repeated as often as required.

Because the course is generated from maintainable source files, there
should be no need to preserve manual changes within the generated
output.

## 6.11 Rebuilding After Changes

If a Word document changes, regenerate the course before rendering
again.

Likewise, regenerate where changes affect:

- course configuration;

- navigation;

- component directives;

- referenced R source;

- supporting resources;

- generated interactions.

The safest general rule is:

If the source has changed, regenerate before publishing.

This ensures that the published course corresponds to the current source
material.

## 6.12 Combined Build Workflow

Where the repository provides orchestration or combined build commands,
these should be preferred over repeatedly running individual stages
manually.

The purpose of orchestration is to turn a multi-stage process such as:

prepare

```text
↓
```

convert Word

```text
↓
```

generate Quarto

```text
↓
```

copy resources

```text
↓
```

configure output

```text
↓
```

render

into a more predictable workflow.

The underlying stages remain important for troubleshooting, but routine
users should use the simplest supported command provided by the
repository.

This is particularly useful when Learning Publisher is run on a shared
development environment or virtual machine.

## 6.13 Publishing the HTML Course

A rendered Quarto website is a collection of static web files.

The complete generated website can therefore be deployed to a suitable
static web hosting environment.

```yaml
Conceptually:
```

Quarto project

```bash
↓
quarto render
↓
```

\_site/

```text
↓
```

Web hosting

The entire generated website should be published rather than uploading
only individual HTML pages.

Supporting directories are required for styling, scripts, navigation and
other functionality.

## 6.14 Moodle Deployment

Learning Publisher output can be used alongside Moodle as a delivery
environment.

A typical model is:

Word source

```text
↓
```

Learning Publisher

```text
↓
```

Quarto course

```text
↓
```

Published web content

```text
↓
```

Moodle access

The exact deployment approach depends on the Moodle environment and
institutional configuration.

Learning Publisher should therefore be viewed primarily as the **content
generation and publishing layer**, rather than as a replacement for
Moodle.

Moodle can continue to provide functions such as:

- enrolment;

- course administration;

- access control;

- institutional navigation;

- assessment;

- learner records.

Learning Publisher provides the generated learning content that can be
incorporated into the wider delivery model.

## 6.15 PDF Output

Where configured, Learning Publisher can also support PDF-oriented
output.

This allows the same maintained source material to contribute to both
web and document-based publication.

```yaml
Conceptually:
→ HTML course
Word + YAML → Quarto
→ PDF
```

This supports the principle of single-source publishing: academic
content is maintained once and transformed into different delivery
formats.

PDF output should still be reviewed separately because page-based
documents have different layout and accessibility requirements from
responsive web content.

## 6.16 Combined Handbook or Document Output

Where the project is configured to generate combined document output,
individual learning pages can be assembled into a larger document.

For example:

```text
Page 1 ─┐
Page 2 ─┤
Page 3 ─┼→ Combined document
Page 4 ─┤
Page 5 ─┘
```

This can be useful for:

- course handbooks;

- review copies;

- archival material;

- printable learning resources;

- alternative formats.

The ordering should be derived from the course structure rather than
maintained manually in a separate document wherever possible.

## 6.17 Publishing from a Virtual Machine

Learning Publisher can also run on a Linux virtual machine.

The overall process remains the same:

Source files

```text
↓
```

Virtual machine

```text
↓
```

Learning Publisher

```text
↓
```

Quarto

```text
↓
```

Generated output

The main difference is that generation occurs in a centrally managed
environment rather than on an individual author's computer.

This can provide a more consistent execution environment for a team
because dependencies and publishing tools can be maintained centrally.

A user may eventually need only to:

upload source

```text
↓
```

run publishing command

```text
↓
```

retrieve output

The precise upload, execution and retrieval process depends on the
infrastructure in which Learning Publisher is deployed.

## 6.18 Separating Source and Output

Source and generated files should remain clearly separated.

```yaml
Conceptually:
project/
├── source/ ← maintain
├── config/ ← maintain
├── code/ ← maintain
├── resources/ ← maintain
│
└── output/ ← generated
```

This makes it immediately clear which files should be edited and which
can be regenerated.

Generated output should not become the only copy of important academic
content.

## 6.19 Version Control

The maintainable Learning Publisher source should be kept under version
control where appropriate.

This can include:

- course configuration;

- Word source documents where suitable;

- R files;

- custom interactions;

- styles;

- templates;

- documentation;

- Learning Publisher configuration.

Generated output may or may not be committed depending on the project's
deployment model.

The important principle is that the source required to reproduce the
course should be identifiable and preserved.

## 6.20 Before Publishing

Before releasing a build, confirm that:

- the expected pages were generated;

- navigation is correct;

- no source documents are missing;

- images display correctly;

- links work;

- downloadable files are available;

- interactive components load;

- R examples display correctly;

- WebR activities execute where used;

- custom interactions work;

- no obvious generation errors remain.

A more detailed QA and accessibility process is covered in Section 7.

## 6.21 Recommended Publishing Workflow

For routine use, the complete process can be understood as:

1. Update Word content

2. Update course.yml if required

3. Update code/resources if required

4. Activate the Python environment

5. Run Learning Publisher

6. Render the generated Quarto project

7. Preview the course in a browser

8. Perform QA and accessibility checks

9. Correct the source where necessary

10. Regenerate and retest

11. Publish the completed output

The central principle remains:

Maintain source

```text
↓
```

Generate

```text
↓
Render
↓
```

Test

```text
↓
```

Publish

This separation between source and generated output is what allows
Learning Publisher courses to remain reproducible and maintainable as
they evolve.

# 7. QA & Accessibility

Quality assurance should be performed on the **generated learner-facing
output**, not only on the Word source documents.

Learning Publisher automates the transformation of structured source
material into published learning content, but generated output still
requires review.

The basic QA cycle is:

Source

```text
↓
```

Generate

```text
↓
Render
↓
```

Review

```text
↓
```

Correct source

```text
↓
```

Regenerate

The aim is to confirm both that the transformation has worked correctly
and that the resulting material remains usable and accessible.

## 7.1 What Should Be Checked

QA should cover four broad areas:

Content

+

Structure

+

Functionality

+

Accessibility

A page may be technically valid while still containing a content error,
inaccessible interaction or broken learning activity.

All four areas therefore need consideration.

## 7.2 Review the Learner-Facing HTML

The rendered HTML is the version that learners will actually use.

After generating and rendering a course, open the published pages in a
browser and check:

- page titles;

- headings;

- paragraphs;

- lists;

- tables;

- images;

- links;

- navigation;

- callouts;

- tabs;

- reveal components;

- quizzes;

- self-check activities;

- R code;

- WebR activities;

- videos;

- downloadable files;

- custom interactions.

Do not assume that content is correct simply because it appeared
correctly in Word.

## 7.3 Check Course Structure

Confirm that the generated course reflects the structure defined in the
course configuration.

Check that:

- all expected sessions appear;

- all expected pages appear;

- page titles are correct;

- pages are in the intended order;

- navigation points to the correct pages;

- no duplicate pages have been generated;

- no obsolete pages remain in the published course.

Structural problems should normally be corrected in the YAML
configuration or source structure rather than in generated Quarto files.

## 7.4 Check Heading Structure

Headings provide both visual organisation and semantic navigation.

Confirm that:

- headings are descriptive;

- heading levels follow a logical hierarchy;

- headings are not created merely through bold or enlarged text;

- sections do not skip levels unnecessarily;

- headings accurately describe the content that follows.

For example:

Page title

Heading 2

Heading 3

Heading 3

Heading 2

Heading 3

is preferable to an inconsistent structure such as:

Page title

Heading 2

Heading 4

Heading 2

Where a heading problem originates in Word, correct the Word heading
style and regenerate the page.

## 7.5 Check Images

Every meaningful image should be reviewed in the generated output.

Confirm that:

- the correct image appears;

- the image is sufficiently clear;

- it is displayed at an appropriate size;

- meaningful alternative text is present;

- alternative text describes the purpose or information conveyed;

- decorative images are handled appropriately;

- essential information is not available only within the image.

For graphs and diagrams, alternative text may need to communicate the
important pattern or conclusion rather than merely naming the type of
image.

For example:

```yaml
Poor:
```

Line graph.

```yaml
Better:
```

Line graph showing incidence rising from approximately

20 to 65 cases per 100,000 between 2010 and 2020.

Complex figures may require surrounding explanatory text in addition to
concise alternative text.

## 7.6 Check Tables

Tables should be reviewed for both correctness and accessibility.

Confirm that:

- table headings are meaningful;

- rows and columns remain correctly aligned;

- the table is understandable when read sequentially;

- unnecessary merged cells have been avoided;

- the table remains usable on smaller displays where relevant.

Tables should be used for genuinely tabular information rather than page
layout.

## 7.7 Check Links

Test important internal and external links.

Check that:

- the destination exists;

- internal navigation points to the intended page;

- downloadable files are available;

- link text is meaningful;

- links do not depend on phrases such as "click here" without context.

```yaml
Prefer:
```

Download the outbreak dataset.

rather than:

Click here.

External websites may change independently of Learning Publisher, so
external links should be reviewed periodically for long-lived courses.

## 7.8 Check Interactive Components

Every interactive component should be tested rather than simply
inspected visually.

For tabs, check that:

- each tab can be selected;

- the correct content appears;

- labels are meaningful;

- keyboard operation works.

For reveal components, check that:

- the reveal control works;

- the hidden content is the intended content;

- the control clearly indicates its purpose.

For self-check activities and quizzes, check that:

- all questions appear;

- all answer options appear;

- the expected response is recognised;

- feedback is correct;

- learners can retry where intended;

- the interaction can be operated without relying solely on a mouse;

- correctness is not communicated through colour alone.

## 7.9 Check R Code

Static R examples should be checked for:

- correct syntax;

- appropriate formatting;

- complete examples;

- consistent coding style;

- correspondence between the explanation and the displayed code.

Where code is stored in an external .R file, the external source should
be treated as the maintainable version.

If code needs correction, edit the source .R file and regenerate the
course.

## 7.10 Check WebR Activities

WebR requires functional testing in the rendered course.

For every WebR activity, confirm that:

- the WebR environment loads;

- initial code appears;

- code can be edited where intended;

- code executes;

- required packages are available;

- required data can be loaded;

- expected output appears;

- errors are displayed appropriately;

- the activity can be operated with a keyboard;

- learner instructions accurately describe the task.

A valid .R file does not by itself demonstrate that the corresponding
WebR activity works correctly.

Test the complete learner-facing activity.

## 7.11 Check Custom Interactions

Custom HTML and JavaScript require additional testing because their
behaviour is not controlled entirely by the standard Learning Publisher
components.

```yaml
Check:
```

- functionality;

- keyboard operation;

- visible focus;

- labels;

- instructions;

- error states;

- responsive behaviour;

- required assets;

- browser behaviour;

- accessibility.

Where an interaction depends on external JavaScript libraries or
services, those dependencies should also be tested.

Custom interactions should provide a meaningful alternative where their
essential learning content cannot otherwise be accessed.

## 7.12 Check Video and Media

Embedded media should be tested in the published environment.

Confirm that:

- the correct media appears;

- the media loads;

- access permissions are correct;

- captions are available where required;

- transcripts or appropriate alternatives are provided where required;

- surrounding text explains the purpose of the media.

For Panopto content in particular, successful embedding does not
guarantee that every learner has permission to view the recording.

Test access using an appropriate learner-level account where possible.

## 7.13 Keyboard Testing

A useful basic accessibility test is to navigate the page without using
a mouse.

Use the keyboard to move through:

- navigation;

- links;

- buttons;

- tabs;

- reveal controls;

- quizzes;

- WebR controls;

- custom interactions.

Check that:

- all interactive elements can be reached;

- focus is visible;

- focus order is logical;

- controls can be activated;

- focus does not become trapped.

Keyboard testing can identify significant usability problems that may
not be apparent during ordinary mouse-based review.

## 7.14 Colour and Visual Meaning

Information should not depend solely on colour.

For example, avoid presenting quiz feedback where the only indication of
correctness is:

```r
green = correct
red = incorrect
```

Provide an additional textual or structural indication such as:

Correct

Incorrect

The same principle applies to charts, warnings, status indicators and
custom interactions.

## 7.15 Accessibility Starts in Word

Many accessibility problems are easier to prevent during authoring than
to repair after publication.

The Word source should therefore use:

- genuine heading styles;

- logical heading hierarchy;

- meaningful alternative text;

- descriptive hyperlinks;

- proper lists;

- meaningful table headings;

- clear instructions;

- understandable language.

Learning Publisher can preserve and transform structured content, but it
cannot infer the author's intended meaning where that meaning has not
been expressed in the source.

## 7.16 Automated Accessibility Testing

Automated accessibility tools can be used as part of the QA process.

Examples include browser-based accessibility auditing tools and
automated page scanners.

These can identify issues such as:

- missing alternative text;

- insufficient contrast;

- missing labels;

- structural problems;

- some ARIA errors;

- certain heading problems.

Automated testing is useful, but it is not sufficient on its own.

A page can pass automated tests while still containing an unusable
interaction or unclear learning activity.

The appropriate model is:

Automated checks

+

Manual review

+

Keyboard testing

+

Content review

=

More reliable QA

## 7.17 Browser Testing

Courses should be tested in an environment representative of learner
use.

At minimum, check the course in a modern supported browser.

For courses containing substantial interactive functionality, additional
browser testing may be appropriate.

Pay particular attention to:

- WebR;

- custom JavaScript;

- embedded media;

- responsive navigation;

- downloadable resources.

If a course has specific institutional browser requirements, those
should determine the final testing matrix.

## 7.18 Responsive Review

Where learners may access the course on different screen sizes, inspect
pages at narrower browser widths.

Look particularly for:

- tables extending beyond the viewport;

- code blocks becoming unusable;

- images being clipped;

- navigation problems;

- interactive controls overlapping;

- custom components relying on fixed dimensions.

Responsive behaviour is especially important for custom HTML and
JavaScript components.

## 7.19 Review PDF Separately

If PDF output is produced, review it separately from the HTML course.

```yaml
Check:
```

- page breaks;

- heading hierarchy;

- tables;

- images;

- captions;

- mathematical content;

- links;

- code blocks;

- content that originated as an interactive component.

An interaction that works on the web cannot necessarily be reproduced
directly in a static PDF.

The PDF therefore needs to remain understandable when interactive
behaviour is unavailable.

## 7.20 Correct the Source, Not the Symptom

When QA identifies a problem, determine where the problem originates.

For example:

Wrong wording

```text
↓
```

Edit Word

Wrong course order

```text
↓
```

Edit YAML

Incorrect R example

```text
↓
```

Edit .R source

Custom interaction error

```text
↓
```

Edit interaction source

Systematic conversion problem

```text
↓
```

Review Learning Publisher transformation

Avoid repeatedly correcting generated .qmd or HTML files.

A correction made at the appropriate source level will be preserved when
the course is regenerated.

## 7.21 Regression Testing

Changes to Learning Publisher itself can affect existing course
features.

After significant changes to the publisher, test representative examples
of the main supported components.

For example:

Ordinary Word content

Headings

Lists

Tables

Images

Links

Tabs

Callouts

Reveal

Self-check

Quiz

```text
R
WebR
```

Media

Custom interactions

This helps identify cases where a new feature or code change has
unintentionally affected an existing component.

A stable demonstration course containing representative components can
be particularly useful for this purpose.

## 7.22 Source and Output Review

It is useful to distinguish two forms of review.

**Source review**

```yaml
Review:
```

- academic accuracy;

- wording;

- structure;

- source images;

- alternative text;

- code;

- configuration.

**Output review**

```yaml
Review:
```

- transformation;

- layout;

- navigation;

- interaction;

- browser behaviour;

- accessibility;

- published resources.

The two stages complement one another.

```text
Word/YAML/code review
```

+

Generated HTML review

=

Complete publishing review

## 7.23 Pre-Publication Checklist

Before publishing a course, confirm:

- All expected pages have been generated.

- Page titles and navigation are correct.

- Heading structures are logical.

- Images display correctly.

- Meaningful images have appropriate alternative text.

- Tables are understandable and correctly structured.

- Important links have been tested.

- Downloadable resources are available.

- Tabs and reveal components work.

- Self-check activities and quizzes work.

- R examples have been checked.

- WebR activities execute successfully.

- Videos and embedded media are accessible.

- Custom interactions have been tested.

- Interactive elements can be operated using a keyboard.

- Focus is visible during keyboard navigation.

- Information does not rely solely on colour.

- The course has been reviewed in the intended browser environment.

- PDF output has been reviewed separately where produced.

- Corrections have been made in the maintainable source rather than only
  in generated files.

- The final course has been regenerated after the last source changes.

## 7.24 QA Principle

The central QA principle is:

Do not validate only the source.

Validate what the learner receives.

Learning Publisher provides a reproducible transformation from
maintainable source material to digital learning content. QA closes that
process by confirming that the transformation has produced the intended
learner experience.

When a problem is identified:

Find the source

```text
↓
```

Correct it

```text
↓
```

Regenerate

```text
↓
```

Retest

This keeps both the course and the publishing workflow maintainable over
time.

Yes. **Section 8 is the final section** in the streamlined handbook
structure we agreed. It should function as the practical reference and
troubleshooting section rather than repeating the earlier explanations.

# 8. Reference & Troubleshooting

This section provides a concise operational reference for common
Learning Publisher tasks and problems.

For detailed explanations of the authoring and publishing workflow,
refer to the earlier sections of this handbook.

## 8.1 Standard Workflow

The normal Learning Publisher workflow is:

Word documents

+

course configuration

+

```text
code/resources
↓
```

Learning Publisher

```text
↓
```

Generated Quarto project

```text
↓
```

Quarto render

```text
↓
```

Learner-facing output

For routine work, remember:

```text
Edit source → Generate → Render → Review → Publish
```

Generated files should not normally become the primary editing source.

## 8.2 Starting a Terminal Session

Move to the Learning Publisher project:

```bash
cd cloudpedagogy-learning-publisher
```

Activate the Python environment:

```bash
source .venv/bin/activate
```

The command prompt will normally indicate that the environment is
```yaml
active:
```

(.venv) user@computer learning-publisher %

If the virtual environment does not yet exist:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 8.3 Check Python

Check that Python is available:

```bash
python --version
```

If required:

```bash
python3 --version
```

When the virtual environment is active, python should normally refer to
the Python interpreter within that environment.

## 8.4 Check Quarto

Check that Quarto is installed:

```bash
quarto --version
```

If a version number is returned, Quarto is available from the current
shell.

If the command is not recognised, install or configure Quarto before
attempting to render the generated course.

## 8.5 Install Python Dependencies

With the virtual environment active:

```bash
pip install -r requirements.txt
```

This installs the Python packages required by the current repository.

If dependencies change after updating Learning Publisher, rerun this
command.

## 8.6 Generate a Course

The generation command uses the Learning Publisher script together with
a course configuration file.

The general pattern is:

```bash
python src/\<publisher-script\>.py config/<course>.yml
```

Use the actual filenames provided by the current repository.

The configuration identifies the course structure, source documents and
associated publishing options.

After generation, inspect the terminal output for warnings or errors
before rendering.

## 8.7 Render a Course

Move to the generated Quarto project if necessary and run:

```bash
quarto render
```

This generates the learner-facing output.

For a Quarto website, the rendered site will normally be placed in the
output directory configured by the project, commonly \_site/.

## 8.8 Preview a Course

During development:

```bash
quarto preview
```

Open the local address reported by Quarto.

Stop the preview server with:

Ctrl+C

Preview mode is preferable to opening individual HTML files directly
when testing interactive components.

## 8.9 Rebuild After Editing

If you edit:

- a Word document;

- the course YAML;

- an external R file;

- a resource;

- a custom interaction;

- another source dependency;

regenerate the course before publishing the new version.

```yaml
Use:
```

Edit

```text
↓
```

Generate

```text
↓
Render
↓
```

Review

Do not assume that changing a source file automatically updates
previously generated output.

## 8.10 Source File Paths

Use relative paths wherever possible.

```bash
Prefer:
source/session1/introduction.docx
and:
code/example.R
```

rather than:

/Users/name/Documents/course/example.R

Relative paths make projects easier to move between computers, virtual
machines and publishing environments.

## 8.11 External R Source

Where an R example is stored externally, use the supported
```bash
source-reference pattern.
```

For example:

Source :: code/example.R

Check that:

- the path is correct;

- the filename is correct;

- the file exists;

- the path is relative to the expected project location;

- the .R file contains valid R code.

If Learning Publisher cannot find the source file, check the path before
changing the conversion code.

## 8.12 Course Does Not Generate

If generation fails, check the terminal error first.

Common causes include:

- virtual environment not activated;

- missing Python dependencies;

- incorrect configuration filename;

- invalid YAML;

- missing Word source document;

- incorrect relative path;

- missing supporting file;

- unsupported or malformed authoring syntax.

Work from the first meaningful error rather than attempting to correct
several unrelated files simultaneously.

A useful diagnostic sequence is:

Did Python start?

```text
↓
```

Was the configuration found?

```text
↓
```

Could the YAML be read?

```text
↓
```

Were the Word files found?

```text
↓
```

Were referenced resources found?

```text
↓
```

Did transformation complete?

## 8.13 Word Document Is Missing

If Learning Publisher reports that a Word source cannot be found:

1.  Check the filename.

2.  Check the path in the YAML configuration.

3.  Check capitalisation.

4.  Confirm that the .docx file exists.

5.  Confirm that the command is being run from the expected location.

On Linux, filename capitalisation matters.

For example:

Introduction.docx

```yaml
and:
```

introduction.docx

may be treated as different files.

This is particularly important when moving a project from macOS or
Windows to a Linux virtual machine.

## 8.14 YAML Errors

YAML depends on indentation and structure.

For example:

```yaml
sessions:
```

\- title: "Introduction"

```yaml
pages:
```

\- title: "Welcome"

```bash
source: "source/welcome.docx"
```

Incorrect indentation can prevent the configuration from being parsed
correctly.

When a YAML error is reported:

- inspect the indicated line;

- check indentation;

- check quotation marks;

- check list markers;

- check for duplicated or malformed keys.

Use spaces rather than tabs for indentation.

## 8.15 Page Is Missing from the Course

If a Word document exists but its page does not appear in the course,
check whether it is included in the course configuration.

A file being present in the source directory does not necessarily mean
that Learning Publisher will publish it.

The relationship should be explicit:

```text
Word document
↓
```

Referenced by course YAML

```text
↓
```

Generated page

Also check that the page has not been deliberately disabled or excluded
through configuration.

## 8.16 Page Order Is Wrong

Page and session order should normally be controlled by the course
configuration.

If pages appear in the wrong order, correct the YAML rather than
manually rearranging generated files.

Then regenerate the course.

## 8.17 Heading Is Incorrect

If a heading is rendered incorrectly:

1.  Open the Word source.

2.  Check the Word style applied to the heading.

3.  Use an actual Word heading style.

4.  Regenerate the course.

Do not fix the heading only in the generated .qmd file.

## 8.18 Image Does Not Appear

If an image is missing:

- confirm that it exists in the Word source or referenced resources;

- check any associated path;

- check whether the image was copied into the generated project;

- inspect the generated page;

- inspect the browser developer console if necessary.

If the image appears in Word but consistently disappears during
generation, the problem may be in the transformation process.

## 8.19 Alternative Text Is Missing

Check the alternative text in the Word source first.

If meaningful alternative text exists in Word but does not appear in the
generated output, investigate whether it has been preserved during
transformation.

Do not add the alternative text only to the final HTML because that
correction will be lost during regeneration.

## 8.20 Link Does Not Work

For a broken link, determine whether it is:

- an external URL;

- an internal course link;

- a downloadable resource;

- a generated navigation link.

For an external URL, verify the destination independently.

For a local resource, check the relative path and confirm that the
resource has been included in the generated output.

For navigation problems, check the course configuration.

## 8.21 Downloadable File Is Missing

Check that the file:

- exists in the project;

- is stored in the expected resources location;

- is referenced using the correct relative path;

- has been copied into the published output.

Remember that publishing an HTML page alone does not automatically
publish every local file on the computer.

## 8.22 Quarto Render Fails

```bash
If:
quarto render
```

fails, identify whether the problem originates in:

Generated Quarto

```text
↓
```

Quarto configuration

```text
↓
```

Referenced resource

```text
↓
Extension/component
↓
```

Rendering dependency

Read the first useful Quarto error message carefully.

If the generated .qmd contains malformed output, determine whether the
underlying Word source or Learning Publisher transformation produced it.

Correct the source of the problem rather than repeatedly patching
generated Quarto.

## 8.23 Preview Works but Published Site Does Not

If the course works with:

```bash
quarto preview
```

but fails after publication, check whether all generated site files were
deployed.

Do not publish only:

index.html

A Quarto site commonly depends on:

index.html

other HTML pages

```text
site_libs/
images/
scripts/
styles/
resources/
```

Publish the complete generated site structure.

Also check for paths that refer incorrectly to files on the development
computer.

## 8.24 WebR Does Not Load

If a WebR activity does not initialise, first establish whether the
problem affects:

- one activity;

- one page;

- or every WebR activity.

```yaml
Check:
```

- browser console errors;

- required WebR assets;

- network dependencies;

- generated JavaScript;

- referenced R files;

- required packages;

- required data.

If all WebR activities fail, investigate the shared WebR setup before
changing individual R examples.

## 8.25 R Code Does Not Run

If WebR loads but the R code fails:

1.  Test the R code independently where appropriate.

2.  Check package availability.

3.  Check object names.

4.  Check data paths.

5.  Check whether the required functionality is supported in the browser
    environment.

6.  Read the WebR error message.

Do not assume that code working in a local desktop R installation will
necessarily work unchanged in WebR.

## 8.26 Custom Interaction Does Not Work

For custom HTML or JavaScript, check:

- file paths;

- JavaScript errors;

- missing libraries;

- missing CSS;

- missing resources;

- browser console output;

- assumptions about the hosting environment.

Test the interaction independently where possible before testing its
integration into Learning Publisher.

This helps distinguish:

interaction problem

```yaml
from:
```

Learning Publisher integration problem

## 8.27 Video Does Not Display

For YouTube or Panopto content, check:

- the video reference;

- embed configuration;

- network access;

- institutional restrictions;

- video permissions.

For Panopto, a technically correct embed can still fail for a learner
who does not have permission to view the recording.

## 8.28 Changes Disappear After Regeneration

If a correction disappears after running Learning Publisher again, it
was probably made in a generated file.

For example:

Word

```text
↓
```

Generated .qmd ← manually edited

```text
↓
```

Regenerate

```text
↓
```

manual edit disappears

Make the correction in the maintainable source instead.

Depending on the issue, this may be:

- Word;

- YAML;

- R;

- a resource;

- an interaction;

- a Learning Publisher template;

- transformation code.

Then regenerate.

## 8.29 Old Content Still Appears

If removed or changed content appears to persist:

- confirm that the correct source was edited;

- regenerate the project;

- rerender the course;

- check that you are viewing the new output;

- refresh the browser;

- check whether old generated files remain in the output directory.

Where appropriate, rebuild from a clean generated output directory.

Be careful not to delete maintainable source material when cleaning
generated files.

## 8.30 Problems After Updating the Repository

After pulling a newer version of Learning Publisher, check whether
dependencies have changed.

With the environment activated:

```bash
pip install -r requirements.txt
```

Then regenerate a known working demonstration course.

This provides a quick check that the updated environment still supports
the expected workflow.

## 8.31 Git Reference

Check repository status:

```bash
git status
```

Pull current changes:

```bash
git pull
```

Stage a changed file:

```bash
git add path/to/file
Commit:
git commit -m "Describe the change"
Push:
git push origin main
```

For several intentional changes:

```bash
git add .
git commit -m "Update Learning Publisher"
git push origin main
```

Always check:

```bash
git status
```

before committing so that unintended files are not included.

## 8.32 Virtual Machine Reference

When Learning Publisher is installed on a Linux virtual machine, the
same core commands apply:

```bash
cd cloudpedagogy-learning-publisher
source .venv/bin/activate
```

Then run the required Learning Publisher and Quarto commands.

A virtual machine changes **where** the software runs, not the
fundamental publishing model:

Source

```text
↓
```

VM

```text
↓
```

Learning Publisher

```text
↓
```

Quarto

```text
↓
```

Output

This makes it possible to provide a consistent environment for multiple
users without requiring every user to configure the complete publishing
stack on their own computer.

## 8.33 Reporting a Problem

When reporting an issue, provide enough information for the problem to
be reproduced.

Useful information includes:

- Learning Publisher version or Git commit;

- operating system;

- Python version;

- Quarto version;

- command used;

- configuration involved;

- relevant source example;

- complete error message;

- whether the problem occurs in the demonstration course;

- whether the problem occurs during generation, rendering or browser
  use.

A useful issue description follows:

What I attempted

What I expected

What happened

Command used

Error message

Minimal source/configuration needed to reproduce it

Avoid reporting only:

It doesn't work.

Reproducible reports make problems substantially easier to diagnose.

## 8.34 Troubleshooting Strategy

When something fails, identify the stage at which it failed.

```text
Word/YAML/resources
↓
```

\[SOURCE\]

```text
↓
```

Learning Publisher

```text
↓
```

\[GENERATION\]

```text
↓
```

Generated Quarto

```text
↓
```

Quarto

```text
↓
```

\[RENDERING\]

```text
↓
```

HTML / PDF

```text
↓
```

\[BROWSER / OUTPUT\]

Then investigate that stage rather than changing unrelated parts of the
project.

```yaml
Ask:
```

**Source problem?**

Check Word, YAML, code and resources.

**Generation problem?**

Check Learning Publisher output and error messages.

**Rendering problem?**

Check Quarto and the generated .qmd.

**Browser problem?**

Check scripts, WebR, media, paths and browser console messages.

This separation is one of the most effective ways to troubleshoot the
publishing pipeline.

## 8.35 Quick Command Reference

Create an environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Check Python:

```bash
python --version
```

Check Quarto:

```bash
quarto --version
```

Generate a course:

```bash
python src/\<publisher-script\>.py config/<course>.yml
Render:
quarto render
Preview:
quarto preview
```

Check Git:

```bash
git status
```

Pull updates:

```bash
git pull
```

Push committed changes:

```bash
git push origin main
```

## 8.36 Final Operating Principle

Learning Publisher is designed around a reproducible publishing model:

Maintain structured source

```text
↓
```

Generate consistently

```text
↓
```

Render reproducibly

```text
↓
```

Review learner-facing output

```text
↓
```

Correct the source

```text
↓
```

Regenerate

The most important troubleshooting rule is therefore:

**Fix the maintainable source or publishing process, not the generated
symptom.**

Following this principle keeps Learning Publisher projects easier to
review, reproduce, maintain and extend as course content and the
publishing system evolve.
