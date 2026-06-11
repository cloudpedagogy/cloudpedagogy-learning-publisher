# Project Specification: CloudPedagogy Learning Publisher

## Overview
CloudPedagogy Learning Publisher is a Python-based publishing system designed to transform structured Word documents into interactive Quarto-based eLearning courses, websites, handbooks, and reusable learning resources.

It automates the scaffolding of Quarto sites and provides a specialized parser to convert specific authoring patterns in Microsoft Word documents into interactive web components, such as quizzes, callouts, tabs, and R code blocks.

## Core Objectives
1. **Separation of Structure and Content**: Provide a hybrid workflow where course architecture is defined cleanly in YAML, while the learning content is authored entirely in Microsoft Word.
2. **Accessible Authoring**: Enable Subject Matter Experts (SMEs) and educators to create complex, interactive eLearning content without needing to write Markdown, Quarto code, or HTML.
3. **Automated Publishing**: Automate the tedious boilerplate required to structure large Quarto websites (navigation, frontmatter, styling).
4. **Multi-format Outputs**: Produce diverse outputs from a single source of truth, including interactive websites, SCORM 1.2 packages for Learning Management Systems (LMS), and printable PDF/Word handbooks.

## Target Audience
- **Instructional Designers**: Who need to structure complex courses and deploy them to an LMS via SCORM.
- **Educators and Subject Matter Experts (SMEs)**: Who prefer authoring content in standard word processors like Microsoft Word.
- **Technical Authors**: Who want to leverage Quarto's powerful computational publishing capabilities (e.g., WebR) without manually scaffolding the site structure.

## Primary User Journey (The Hybrid Workflow)
The system advocates for a hybrid approach to course creation:

1. **Architect the Course (YAML)**: The Instructional Designer or Lead Educator creates a `course.yml` file defining the Modules, Sessions, Sections, and Pages.
2. **Generate Scaffold**: The user runs `coursegen build` to translate the YAML into a complete folder structure of Quarto `.qmd` files.
3. **Author Content (Word)**: SMEs write content in Microsoft Word documents, utilizing simple, predefined syntax (e.g., `Quiz`, `R Code :: webr`) to denote interactive elements.
4. **Import and Transform**: The user runs `coursegen import_word`, which parses the `.docx` files, translates the syntax into Quarto/HTML components, and injects them into the generated scaffold.
5. **Publish**: The user runs `coursegen render` to build the Quarto website, or utilizes standalone scripts to package the output as SCORM or a Handbook.

## Key Terminology
- **Scaffold**: The directory structure of `.qmd` files and Quarto configuration files generated from the YAML config.
- **Interaction Directives**: The specific syntax used in Word documents (e.g., `Callout ::`) that the parser recognizes and transforms into interactive web elements.
- **WebR**: A technology that runs R natively in the browser. The publisher can automatically generate WebR blocks from Word documents.

## Relationship to CloudPedagogy Course Engine
While the **Learning Publisher** is focused strictly on the *content creation and publishing layer* (transforming documents into websites and PDFs), the broader **CloudPedagogy Course Engine** is focused on the *production, validation, and orchestration layer* (reproducible builds, traceable outputs, and governance). 

Currently, the Learning Publisher operates as an independent, standalone tool. Future roadmap discussions will determine if it should remain standalone or be merged as a component of the Course Engine.
