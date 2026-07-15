# Quarto Publishing Platform

The Quarto Publishing Platform is a Word-first publishing system that enables educators to create websites, handbooks, presentations, Moodle resources and interactive learning experiences from a single editable Microsoft Word source.

## Overview

The platform enables authors to continue working in Microsoft Word while
automatically producing Quarto websites, printable handbooks, PDF
handbooks, RevealJS presentations, Twine scenarios, Moodle Books and
audit reports.

## Documentation

📖 **User Handbook** – *Coming Soon*

A comprehensive guide covering installation, course creation, publication assembly, Moodle integration, handbook generation and advanced publishing workflows.

🛠️ **Developer Guide** – *Coming Soon*

Documentation covering the platform architecture, project structure, APIs and how to develop new publishing tools and extensions.

## Requirements

-   Python 3.14+
-   Quarto
-   Pandoc
-   TinyTeX (for PDF output)
-   Git

Verify installation:

``` bash
python3 --version
quarto --version
pandoc --version
```

Install TinyTeX:

``` bash
quarto install tinytex
```

## Installation

Clone the repository:

``` bash
git clone <repository-url>
cd <repository-folder>
```

Create a virtual environment:

``` bash
python3 -m venv .venv
```

Activate (macOS/Linux):

``` bash
source .venv/bin/activate
```

Activate (Windows PowerShell):

``` powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

``` bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify:

``` bash
python -c "import mammoth,pandas,plotly,bs4; print('Installation successful')"
```

## Project Structure

``` text
assemblies/
build/
config/
docs/
imports/
output/
src/
```

### Source folders

`imports/` stores original source material such as Word documents,
Moodle Book ZIP files and Moodle MBZ backups.

### Generated folders

`build/` contains temporary generated files.

`output/` contains published websites, reports and dashboards.

## Features

-   Word → Quarto
-   HTML websites
-   Printable HTML handbooks
-   PDF handbooks
-   WebR
-   Mermaid
-   RevealJS
-   Twine
-   Word → Moodle Book
-   Moodle Book → Word
-   Moodle Book QA
-   Moodle Course (.mbz) Auditor
-   Plotly dashboards
-   Publication assembly

## Repository Guidance

Commit:

-   src/
-   docs/
-   config/
-   assemblies/
-   requirements.txt
-   README.md

Do not commit:

-   .venv/
-   build/
-   output/
-   imports/
-   **pycache**/

Always create a fresh virtual environment after cloning:

``` bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```