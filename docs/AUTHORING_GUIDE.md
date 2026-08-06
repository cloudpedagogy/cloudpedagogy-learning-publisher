# Learning Publisher Authoring Guide

This guide explains how to create and maintain Word-first courses with CloudPedagogy Learning Publisher. It is intended for course authors, learning technologists and reviewers. Repository installation and developer information remain in `README.md`.

## 1. Authoring model

Each course is self-contained:

```text
imports/courses/my_course/
├── course.yml
├── docx/
├── code/
└── resources/
    ├── data/
    ├── html/
    ├── images/
    ├── pdf/
    └── video/
```

- `course.yml` defines the course hierarchy, titles, identifiers and Word sources.
- `docx/` contains the editable Word documents.
- `code/` contains external `.R` and `.js` files referenced from Word.
- `resources/` contains images, downloads, media and standalone HTML activities.

Treat the Word documents and files in the course folder as source material. Files under `build/` and `output/` are generated and should not be edited as the master copy.

## 2. Recommended author workflow

1. Edit the appropriate `.docx` file in the course's `docx/` folder.
2. Add or update any referenced files under `code/` or `resources/`.
3. Accept or reject tracked changes before publishing a completed version.
4. Save and close Word. Remove temporary Word lock files whose names begin with `~$`.
5. Run the publishing commands from the repository root.
6. Review the website and, where relevant, the Word and PDF handbook outputs.

```bash
source .venv/bin/activate

python -m course_generator.cli validate imports/courses/my_course/course.yml
python -m course_generator.cli build imports/courses/my_course/course.yml
python -m course_generator.cli import-word imports/courses/my_course/course.yml
python src/course_generator/tools/build_handbook_from_quarto.py build/courses/my_course
python -m course_generator.cli render imports/courses/my_course/course.yml --no-versioned
```

Replace `my_course` with the course folder name. On macOS, open the result with:

```bash
open output/courses/my_course/index.html
```

Run `build` before `import-word`. After changing Word, R, JavaScript or resources, rerun `import-word`, the handbook step and `render`.

## 3. Word document structure

Use Word styles consistently:

- Use built-in heading styles for headings; do not simulate headings with bold text.
- Use Word list tools for numbered and bulleted lists.
- Use real Word tables rather than tabs or spaces.
- Add meaningful alternative text to informative images.
- Use descriptive link text rather than “click here”.
- Keep directive keywords as ordinary text on separate paragraphs.

The page title and position in the course are controlled by `course.yml`. Avoid adding a second top-level page title in Word unless the design specifically requires it.

### Directive rules

- Write the separator as two colons: `::`.
- Put opening and closing markers on separate lines.
- Use the explicit `END ...` marker for every bounded block.
- Do not place one interaction directive inside another unless the component explicitly supports it.
- Keep source paths relative to the course folder.
- Do not use absolute paths or `../` paths that leave the course folder.

Directive keywords are case-insensitive, but the capitalisation shown here is recommended for consistency.

## 4. Course configuration

The course-local `course.yml` defines a module containing sessions, sections and subpages:

```yaml
module:
  id: EXAMPLE_01
  code: EXAMPLE_01
  title: "Example Course"
  description: "A short example course."
  default_render_mode: multi_page
  default_subpage_count: 1

sessions:
  - id: EXAMPLE_01-se01
    code: SE01
    title: "Introduction"
    type: standard
    required: true
    overview: "An introduction to the topic."
    learning_objectives:
      - "Explain the main concept."
      - "Apply the concept to an example."
    render_mode: multi_page
    sections:
      - id: EXAMPLE_01-se01-sec01
        title: "Core concept"
        kind: section_overview
        number: 1
        navigation_style: numbered_subpages
        subpage_count: 1
        subpages:
          - id: EXAMPLE_01-se01-sec01-sp01
            title: "Core concept"
            kind: text_page
            source_docx: "docx/01_core_concept.docx"
```

Use stable, unique IDs. Changing an ID can change URLs and break existing links. The `source_docx` path is resolved from the folder containing `course.yml`.

A standalone page such as a glossary can be added at the top level:

```yaml
standalone_pages:
  - id: EXAMPLE_01-glossary
    title: "Glossary"
    kind: text_page
    source_docx: "docx/course_glossary.docx"
```

Run `validate` after editing `course.yml` and resolve errors before building.

## 5. Reveals

Use a reveal for optional supporting detail, a model answer or a worked step. Essential information should not be hidden by default.

```text
Reveal
Label :: Show the worked calculation

Add the content to reveal here. Normal paragraphs, lists, tables and equations may be used.

END Reveal
```

If `Label ::` is omitted, the label defaults to “Show more”.

## 6. Self-checks

A self-check presents a question followed by a hidden suggested answer.

```text
SelfCheck
Question :: Why might vaccine effectiveness differ between populations?
Answer :: Differences in exposure, behaviour and population structure can influence estimates.

Further answer paragraphs and lists can follow the answer line.

END SelfCheck
```

Write a question that learners can answer before opening the suggested response. Include enough explanation for the feedback to be useful.

## 7. Callouts

Supported callout types are `note`, `tip`, `warning`, `caution` and `important`.

```text
Callout :: important
Title :: Interpretation

Vaccine effectiveness compares disease risk in vaccinated and unvaccinated groups.

END Callout
```

`Title ::` is optional. For a short single paragraph, `Text ::` is also accepted:

```text
Callout :: note
Text :: This estimate applies to the study population and period.
END Callout
```

Use callouts selectively. Too many callouts weaken the visual hierarchy.

## 8. Tabs

Tabs are useful for parallel material such as alternative methods or comparable scenarios.

```text
Tabs
Tab :: Interpretation

Add interpretation content here.

END Tab
Tab :: Limitations

Add limitations here.

END Tab
END Tabs
```

Each tab may contain ordinary Word content. Do not nest other metadata-driven interaction blocks inside a tab. Avoid tabs when learners must compare all content simultaneously or when the content is essential in sequence.

## 9. Quizzes

### Simple single-select quiz

`Type :: single` is the default and may be omitted. The `Answer ::` text must match one `Option ::` value.

```text
Quiz
Question :: What does vaccine effectiveness of 80% mean?
Option :: Vaccinated people have zero risk
Option :: Vaccinated people have an 80% lower risk than unvaccinated people
Option :: 80% of the population is vaccinated
Answer :: Vaccinated people have an 80% lower risk than unvaccinated people
Hint :: Compare disease risk between the two groups.
Explanation :: Vaccine effectiveness is a relative reduction in risk, not a guarantee of zero risk.
END Quiz
```

### Multiple-select quiz

Use one `Answer ::` line for each correct option:

```text
Quiz
Type :: multiple
Question :: Which factors can influence an observed vaccine-effectiveness estimate?
Option :: Exposure patterns
Option :: Case definition
Option :: Confounding
Option :: Font size in the report
Answer :: Exposure patterns
Answer :: Case definition
Answer :: Confounding
Explanation :: Study design, measurement and population differences can affect the estimate.
END Quiz
```

### Rich answer options

Rich option blocks allow formatted content and option-specific feedback:

```text
Quiz
Question :: Which interpretation is most appropriate?
Option
Correct :: true
Text :: The estimate describes a relative reduction in risk.
Feedback :: Correct. It compares risk between groups.
END Option
Option
Correct :: false
Text :: The vaccine prevents every possible infection.
Feedback :: This overstates what the estimate shows.
END Option
Explanation :: Effectiveness estimates are comparative and context-dependent.
END Quiz
```

Always provide at least two options, identify the correct answer and include explanatory feedback. Avoid trick questions and ambiguous wording.

## 10. R content

### Display-only R example

Use `R Example` when code should be shown but not executed:

```text
R Example
fit <- glm(outcome ~ vaccinated, family = binomial(), data = outbreak)
summary(fit)
END R Example
```

### Inline executable R

```text
R Code
R Mode :: static
Echo :: true
Output :: true
Alt :: Line chart showing infections rising to a peak and then declining.
Caption :: Simulated epidemic curve
plot(epidemic_day, infections, type = "l")
END R Code
```

### External R file

For reusable or substantial code, place one `.R` file in the course's `code/` folder:

```text
R Code
Source :: code/outbreak-risk-table.R
R Mode :: static
Echo :: true
Output :: true
Alt :: Table comparing attack rates by vaccination status.
Caption :: Outbreak risk table
END R Code
```

Do not include both `Source ::` and inline R in the same block.

R options:

| Field | Values | Purpose |
| --- | --- | --- |
| `R Mode ::` or `Mode ::` | `static`, `webr` | Run at render time or provide a browser-based WebR activity. |
| `Echo ::` | `true`, `false` | Show or hide static R source code. |
| `Output ::` | `true`, `false` | Execute/show output, or present a code-only static example. |
| `Alt ::` | Text | Describe the meaning of a generated figure. |
| `Caption ::` | Text | Provide a visible caption. |

Static R requires R and the necessary packages on the publishing computer. WebR support depends on the configured Quarto WebR extension.

## 11. Plain JavaScript interactions

Use this component for a self-contained interaction supplied as one course-local `.js` file:

```text
JavaScript Interaction
Source :: code/sir-model-interaction.js
Container ID :: sir-model
Interaction :: sir-model
Alt :: Interactive SIR epidemic model showing susceptible, infectious and recovered populations over time.
Caption :: Explore how transmission and recovery affect an epidemic
END JavaScript Interaction
```

Required fields:

- `Source ::` must point to a `.js` file inside the course folder.
- `Container ID ::` must be unique on the page and begin with a letter.
- `Interaction ::` supplies a short machine-readable interaction name.

`Alt ::` and `Caption ::` should also be supplied. The alternative text should state the purpose of the activity, not merely call it “interactive”.

The JavaScript file is inserted directly into the generated page. It should:

- Locate the container by its configured ID or interaction attribute.
- Create its own controls, presentation and behaviour inside that container.
- Work without external internet dependencies where possible.
- Use labelled form controls and keyboard-operable buttons.
- Expose changing results as text as well as graphics.
- Avoid a literal closing `</script>` tag in the source.
- Avoid assuming that it is the only interaction on the page.

Plain JavaScript interactions are different from standalone HTML embeds. Use the HTML component when the activity is already a complete HTML document.

## 12. Images and downloadable files

Store course resources under the appropriate `resources/` subfolder.

### Image

```text
Image :: resources/images/epidemic-curve.png
Alt :: Epidemic curve with cases peaking on day 18.
Caption :: Daily cases during the simulated outbreak
Width :: 80%
END Image
```

Use empty alternative text only for genuinely decorative images. Do not repeat the caption word-for-word in the alternative text; describe the information conveyed by the image.

### Downloadable file

```text
File :: resources/data/outbreak-dataset.zip
Label :: Download the outbreak dataset
Display :: link
END File
```

Use a descriptive label and identify the file type or purpose when that helps learners.

## 13. Video and standalone HTML

### YouTube

```text
YouTubeEmbed :: https://www.youtube.com/watch?v=VIDEO_ID
```

### Panopto

```text
PanoptoEmbed :: https://example.hosted.panopto.com/Panopto/Pages/Embed.aspx?id=VIDEO_ID
```

Provide captions or a transcript for instructional video. Confirm that permissions allow the intended learners to view it.

### Local standalone HTML

The HTML file must be trusted, local and stored under `resources/html/`:

```text
HTML Embed :: resources/html/distribution-demo.html
Title :: Interactive distribution demonstration
Height :: 700
Fallback Image :: resources/images/distribution-demo-fallback.png
END HTML Embed
```

Use `Fallback Image ::` when a static representation is useful in non-HTML outputs. Test keyboard access, resizing and offline behaviour.

## 14. Accessibility checklist

Before marking a page complete, confirm that:

- Heading levels form a logical hierarchy.
- Links describe their destination or action.
- Images and generated charts have meaningful alternative text.
- Tables have a clear header row and a simple structure where possible.
- Video has captions and important audio information is available in text.
- Colour is not the only way information is conveyed.
- Interactions work with a keyboard and have visible focus states.
- Questions have meaningful feedback rather than only “correct” or “incorrect”.
- Hidden content is supplementary and has a clear reveal label.
- Acronyms and specialist terms are explained.

Accessibility should be checked in the rendered outputs, not only in Word.

## 15. Review and quality assurance

Review at least the following after every substantive import:

1. Navigation, titles and page order.
2. Headings, lists, tables and links.
3. Images, downloads and embedded media.
4. Every reveal, self-check, tab and quiz.
5. R code, figures, tables and WebR controls.
6. JavaScript interactions at desktop and narrow screen widths.
7. The combined handbook, especially page breaks and interaction fallbacks.
8. Importer warnings shown in Terminal.

Use tracked changes during review, but accept/reject all changes before treating a Word file as complete. Reimport after any accepted correction.

## 16. Troubleshooting

### The virtual environment cannot be activated

If `.venv/bin/activate` does not exist, perform the one-time setup from the repository root:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### A directive appears as ordinary text

Check that:

- the directive is on its own line;
- `::` uses two colons;
- the opening keyword is spelled correctly;
- the block has the correct `END ...` line; and
- the document was saved before `import-word` was rerun.

### An external source file is not found

Paths are relative to the course folder, not the repository root or Word document. For example:

```text
Source :: code/example.R
```

Confirm the filename, extension and letter case. Absolute paths and paths outside the course folder are rejected.

### Changes do not appear in the website

Rerun the full authoring cycle:

```bash
python -m course_generator.cli build imports/courses/my_course/course.yml
python -m course_generator.cli import-word imports/courses/my_course/course.yml
python src/course_generator/tools/build_handbook_from_quarto.py build/courses/my_course
python -m course_generator.cli render imports/courses/my_course/course.yml --no-versioned
```

Then refresh the browser. If necessary, close the old page and reopen `output/courses/my_course/index.html`.

### PDF rendering fails

Check that TinyTeX is installed:

```bash
quarto install tinytex
```

Also check the first error in the render log; later errors are often consequences of the first one.

### Word temporary files are imported accidentally

Close Word and delete files beginning with `~$`. These are temporary lock files and should not be committed.

## 17. Source-control guidance

Normally commit:

- `course.yml`;
- source `.docx` files;
- files under `code/` and `resources/`;
- platform source changes under `src/`; and
- documentation such as this guide.

Normally ignore:

- `.venv/`;
- `__pycache__/` and `*.pyc`;
- Word lock files beginning with `~$`;
- temporary ZIP downloads; and
- generated `build/` and `output/` folders, unless the repository intentionally publishes them.

## 18. Author handover checklist

Before handing a course to another author or publishing it:

- [ ] `course.yml` validates successfully.
- [ ] All source files are stored inside the course folder.
- [ ] Word tracked changes have been resolved.
- [ ] Directive blocks have explicit end markers.
- [ ] All figures and interactions have accessible descriptions.
- [ ] Links, downloads and video permissions have been tested.
- [ ] The website has been reviewed at desktop and narrow widths.
- [ ] The handbook outputs have been checked.
- [ ] Import and render warnings have been resolved or documented.
- [ ] Generated and temporary files are excluded from the commit as intended.

