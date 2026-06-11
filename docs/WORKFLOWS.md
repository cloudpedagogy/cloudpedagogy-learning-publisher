# Publishing Workflows: CloudPedagogy Learning Publisher

The repository was designed to abstract the complexity of Quarto site generation away from content authors. This is achieved through a **Hybrid Workflow** that splits structural architecture from content authoring.

---

## The Primary Hybrid Workflow (YAML + Word)

This is the recommended, primary pathway for creating courses using the Learning Publisher.

### Step 1: Architect the Course Structure (YAML)
The Instructional Designer creates a `course.yml` configuration file. This file defines the entire nested hierarchy of the course. It also points to the specific Microsoft Word (`.docx`) files that will contain the content for each page.

```yaml
module:
  id: my_course
  title: "Introduction to Epidemiology"

sessions:
  - code: SE01
    title: "Session 1: Basics"
    sections:
      - number: 1
        title: "Welcome"
        pages:
          - id: intro1
            title: "What is Epidemiology?"
            source_docx: "imports/my_course/docx/intro.docx"
```

### Step 2: Build the Scaffold
Run the build command to translate the YAML into a physical directory of Quarto (`.qmd`) files.
```bash
coursegen build config/course.yml
```
This generates `course/my_course/` containing `index.qmd`, `se01/index.qmd`, and `se01/01-welcome/intro1.qmd`.

### Step 3: Author Content in Word
The Subject Matter Expert (SME) opens Microsoft Word and writes the content for `intro.docx`. They can use simple text directives to invoke complex web components:

**Example Word Authoring Syntax:**
```text
Here is a normal paragraph of text written in Word.

Callout :: tip
Text :: Remember that R0 is the basic reproduction number.

Quiz
Question :: What is Epidemiology?
Option :: The study of skin
Option :: The study of health and disease in populations
Answer :: The study of health and disease in populations
Explanation :: Epidemiology focuses on populations rather than individuals.

R Code
R Mode :: webr
# Try calculating the mean yourself
mean(c(1, 2, 3, 4, 5))
END R Code
```

### Step 4: Import and Transform
Run the import command.
```bash
coursegen import_word config/course.yml
```
The system reads the Word document, converts it to Markdown via Pandoc, recognizes the `Quiz`, `Callout`, and `R Code` syntax, and safely injects Quarto directives and HTML into the `intro1.qmd` file generated in Step 2.

### Step 5: Render and Package
Finally, render the completed Quarto site and generate LMS/Handbook formats.
```bash
coursegen render config/course.yml
python src/course_generator/tools/package_scorm.py --site-dir output/my_course --title "Epi 101"
python src/course_generator/tools/build_handbook_from_quarto.py course/my_course
```

---

## The Direct Authoring Workflow (Advanced)

If you are comfortable writing Quarto Markdown directly, you can bypass the Word import phase entirely.

1. **Step 1 & 2:** Architect and Build the Scaffold via YAML exactly as above.
2. **Author in Quarto:** Open the generated `.qmd` files in VS Code, RStudio, or your preferred code editor. Write your Markdown and Quarto directives directly into the file.
3. **Render:** Run `coursegen render`. 

*Note: If you use the Direct Authoring Workflow, do not run `coursegen import_word` for those specific pages, as it may overwrite manually authored content outside of the designated import blocks.*
