# Installation Guide: CloudPedagogy Learning Publisher

This guide outlines the software requirements and steps to install and set up the CloudPedagogy Learning Publisher.

## System Requirements

To use the full hybrid workflow (YAML + Word), your system must have the following software installed:

### 1. Python (3.10+)
The core logic of the Learning Publisher is written in Python. 
- **macOS:** We recommend installing Python via [Homebrew](https://brew.sh/): `brew install python`
- **Windows:** Download the installer from [python.org](https://www.python.org/downloads/).

### 2. Quarto
Quarto is the underlying publishing engine used to render the final websites and documents.
- Download and install the latest version from the [Quarto website](https://quarto.org/docs/get-started/).
- **macOS (Homebrew):** `brew install --cask quarto`

### 3. Pandoc
Pandoc is required by the `import_word` command to convert Microsoft Word (`.docx`) files into Markdown.
- **macOS:** `brew install pandoc`
- **Windows:** Download the installer from the [Pandoc releases page](https://github.com/jgm/pandoc/releases/).

### 4. TinyTeX / LaTeX (Optional, but recommended)
If you intend to generate PDF handbooks using the `build_handbook_from_quarto.py` script, you must have a LaTeX distribution installed. Quarto recommends TinyTeX.
- To install TinyTeX via Quarto, run the following in your terminal:
  ```bash
  quarto install tinytex
  ```

---

## Project Setup & Installation

We highly recommend using a Python Virtual Environment (`venv`) to prevent dependency conflicts with other Python projects on your system.

### 1. Clone the Repository
Clone the project to your local machine and navigate into the directory:
```bash
git clone <repository_url>
cd cloudpedagogy-learning-publisher
```

### 2. Create and Activate a Virtual Environment
**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

*Note: You must ensure your virtual environment is activated every time you open a new terminal window to work on this project.*

### 3. Install the Package and Dependencies
Install the CLI tool and its required Python packages (Click, PyYAML, Jinja2, Pydantic, Rich). The `-e` flag installs it in "editable" mode, meaning any changes to the source code will immediately take effect.
```bash
pip install -e .
```

---

## Verification

### 1. Test the CLI
Verify that the `coursegen` CLI tool is installed correctly by checking the help menu:
```bash
coursegen --help
```
You should see a list of available commands (`build`, `import_word`, `render`, etc.).

### 2. Run Automated Tests
If you want to ensure the internal logic is functioning correctly, you can run the provided pytest suite:
```bash
pip install pytest
pytest tests/
```

### 3. Run a Basic Render
You can perform a dry run using the provided demo configuration to ensure Quarto is working correctly:
```bash
coursegen build config/outbreak_ve_demo.yml
coursegen render config/outbreak_ve_demo.yml
```
This should generate a `course/outbreak_ve_demo/` folder and render the Quarto site into `output/outbreak_ve_demo/`.

---

## Troubleshooting Common Issues

### "command not found: coursegen"
**Issue:** You installed the package, but the CLI command isn't recognized.
**Solution:** Ensure your virtual environment is activated (`source venv/bin/activate`). If you installed it without a virtual environment, ensure your Python User `bin` directory is in your system's `PATH`.

### "Pandoc conversion failed" during `import_word`
**Issue:** The system cannot find Pandoc when trying to import a Word document.
**Solution:** Verify Pandoc is installed and accessible in your terminal by running `pandoc --version`. If it is not found, install it via Homebrew (macOS) or the official installer (Windows).

### "Quarto Render Error" or Quarto not found
**Issue:** The `render` or `preview` command fails because Quarto is missing.
**Solution:** Verify Quarto is installed by running `quarto --version`. Restart your terminal if you just installed it.

### PDF Compilation Errors
**Issue:** Running the `build_handbook_from_quarto.py` script fails when trying to output a PDF.
**Solution:** This is almost always due to a missing LaTeX installation. Ensure you have run `quarto install tinytex` as detailed in the System Requirements.
