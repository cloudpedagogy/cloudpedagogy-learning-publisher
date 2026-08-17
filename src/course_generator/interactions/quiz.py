import html
import re

import click


def parse_quiz(content: str) -> tuple[str, int]:
    """
    Render accessible single- or multiple-select quizzes with answer checking.

    Type :: defaults to single for backwards compatibility. Repeated Answer ::
    lines define the correct set for simple Option :: choices. Rich choices use
    bounded Option/END Option blocks with Correct :: and optional Feedback ::.
    Hint :: is optional.
    Explanation :: begins rich explanation content; subsequent paragraphs,
    lists, tables and equations are preserved until END Quiz.
    """
    lines = content.split("\n")
    new_lines = []
    count = 0
    i = 0
    quiz_index = 0

    def normalize_plain_text(text: str) -> str:
        """Undo safe Pandoc escapes used in simple quiz text fields."""
        return text.replace(r'\"', '"')

    def esc(text: str) -> str:
        """
        Escape visible quiz text for an HTML text node.

        Ampersands and angle brackets must be escaped. Quotes are deliberately
        left as literal characters because they are safe in text-node content
        and should display to learners as ordinary quotation marks.
        """
        return html.escape(normalize_plain_text(text), quote=False)

    while i < len(lines):
        stripped = lines[i].strip()

        if not re.match(r"^(?:#+\s*)?Quiz\s*$", stripped, re.IGNORECASE):
            new_lines.append(lines[i])
            i += 1
            continue

        question = ""
        options = []
        quiz_type = "single"
        answers = []
        hint = ""
        explanation_lines = []
        explanation_started = False
        i += 1
        quiz_index += 1
        quiz_name = f"quiz_{quiz_index}"
        found_end = False

        while i < len(lines):
            current_line = lines[i]
            s = current_line.strip()

            if re.match(r"^(?:#+\s*)?END Quiz\s*$", s, re.IGNORECASE):
                found_end = True
                i += 1
                break

            q_match = re.match(r"^Question\s*::\s*(.*)$", s, re.IGNORECASE)
            t_match = re.match(r"^Type\s*::\s*(.*)$", s, re.IGNORECASE)
            o_match = re.match(r"^Option\s*::\s*(.*)$", s, re.IGNORECASE)
            a_match = re.match(r"^Answer\s*::\s*(.*)$", s, re.IGNORECASE)
            h_match = re.match(r"^Hint\s*::\s*(.*)$", s, re.IGNORECASE)
            e_match = re.match(r"^Explanation\s*::\s*(.*)$", s, re.IGNORECASE)

            if re.match(r"^(?:#+\s*)?Option\s*$", s, re.IGNORECASE):
                option_content = []
                option_feedback = []
                option_correct = False
                feedback_started = False
                option_found_end = False
                i += 1

                while i < len(lines):
                    option_line = lines[i]
                    option_s = option_line.strip()

                    if re.match(r"^(?:#+\s*)?END Option\s*$", option_s, re.IGNORECASE):
                        option_found_end = True
                        i += 1
                        break
                    if re.match(r"^(?:#+\s*)?END Quiz\s*$", option_s, re.IGNORECASE):
                        break

                    correct_match = re.match(r"^Correct\s*::\s*(.*)$", option_s, re.IGNORECASE)
                    feedback_match = re.match(r"^Feedback\s*::\s*(.*)$", option_s, re.IGNORECASE)
                    text_match = re.match(r"^Text\s*::\s*(.*)$", option_s, re.IGNORECASE)

                    if (
                        correct_match
                        and not any(line.strip() for line in option_content)
                        and not feedback_started
                    ):
                        option_correct = correct_match.group(1).strip().lower() in {
                            "yes", "true", "correct", "1"
                        }
                    elif feedback_match:
                        feedback_started = True
                        option_feedback.append(feedback_match.group(1).strip())
                    elif feedback_started:
                        option_feedback.append(option_line)
                    elif text_match:
                        option_content.append(
                            normalize_plain_text(text_match.group(1).strip())
                        )
                    else:
                        option_content.append(option_line)
                    i += 1

                while option_content and not option_content[0].strip():
                    option_content.pop(0)
                while option_content and not option_content[-1].strip():
                    option_content.pop()
                while option_feedback and not option_feedback[0].strip():
                    option_feedback.pop(0)
                while option_feedback and not option_feedback[-1].strip():
                    option_feedback.pop()

                options.append({
                    "content": option_content,
                    "plain_text": " ".join(line.strip() for line in option_content if line.strip()),
                    "correct": option_correct,
                    "feedback": option_feedback,
                    "rich": True,
                })
                if not option_found_end:
                    click.echo(
                        click.style(
                            "Warning: rich Option block has no END Option tag.",
                            fg="yellow",
                        )
                    )
                continue
            elif q_match:
                question = normalize_plain_text(q_match.group(1).strip())
            elif t_match:
                candidate_type = t_match.group(1).strip().lower()
                quiz_type = candidate_type if candidate_type in {"single", "multiple"} else "single"
            elif o_match:
                option_text = normalize_plain_text(o_match.group(1).strip())
                options.append({
                    "content": [option_text],
                    "plain_text": option_text,
                    "correct": False,
                    "feedback": [],
                    "rich": False,
                })
            elif a_match:
                answers.append(normalize_plain_text(a_match.group(1).strip()))
            elif h_match:
                hint = normalize_plain_text(h_match.group(1).strip())
            elif e_match:
                explanation_started = True
                explanation_lines.append(e_match.group(1).strip())
            elif explanation_started:
                explanation_lines.append(current_line)

            i += 1

        new_lines.append("")
        new_lines.append("## Quiz")
        new_lines.append("")

        if question:
            new_lines.append(question)
            new_lines.append("")

        if options:
            input_type = "checkbox" if quiz_type == "multiple" else "radio"
            instruction = "Select all that apply." if quiz_type == "multiple" else "Select one answer."
            correct_answers = {answer.casefold() for answer in answers}
            for option in options:
                if option["plain_text"].casefold() in correct_answers:
                    option["correct"] = True
            # Pandoc fenced divisions keep rich Markdown, equations and code
            # structurally valid in HTML, PDF and DOCX. Raw nested HTML divs
            # caused unclosed-Div warnings in combined handbooks.
            new_lines.append(
                f':::::: {{#{quiz_name} .quiz-block data-quiz-type="{quiz_type}"}}'
            )
            new_lines.append("")
            new_lines.append(f'*{instruction}*')
            new_lines.append("")
            for idx, option in enumerate(options, start=1):
                option_id = f"{quiz_name}_opt_{idx}"
                content_id = f"{option_id}_content"
                is_correct = "true" if option["correct"] else "false"
                new_lines.append('::::: {.quiz-option}')
                new_lines.append(':::: {.quiz-option-control}')
                new_lines.append(
                    f'<input type="{input_type}" id="{option_id}" name="{quiz_name}" '
                    f'data-correct="{is_correct}" aria-labelledby="{content_id}">'
                )
                new_lines.append("")
                if option["rich"]:
                    new_lines.append(
                        f'::: {{#{content_id} .quiz-option-content data-for="{option_id}"}}'
                    )
                    new_lines.append("")
                    new_lines.extend(option["content"])
                    new_lines.append("")
                    new_lines.append(':::')
                else:
                    new_lines.append(
                        f'<label id="{content_id}" class="quiz-option-content" '
                        f'for="{option_id}">{esc(option["plain_text"])}</label>'
                    )
                new_lines.append("")
                new_lines.append('::::')
                if option["feedback"]:
                    new_lines.append(':::: {.quiz-option-feedback hidden="hidden"}')
                    new_lines.append("")
                    new_lines.extend(option["feedback"])
                    new_lines.append("")
                    new_lines.append('::::')
                new_lines.append(':::::')
                new_lines.append("")
            new_lines.append(
                '<p class="quiz-actions">'
                '<button type="button" class="quiz-check">Check answer</button> '
                '<button type="reset" class="quiz-reset">Try again</button>'
                '</p>'
            )
            new_lines.append('<p class="quiz-feedback" role="status" aria-live="polite"></p>')
            new_lines.append("")
            new_lines.append('::::: {.quiz-explanation hidden="hidden"}')
            new_lines.append("")
            if explanation_lines:
                new_lines.append("**Explanation:**")
                new_lines.append("")
                while explanation_lines and not explanation_lines[0].strip():
                    explanation_lines.pop(0)
                while explanation_lines and not explanation_lines[-1].strip():
                    explanation_lines.pop()
                new_lines.extend(explanation_lines)
            new_lines.append("")
            new_lines.append(':::::')
            new_lines.append("")
            new_lines.append('::::::')
            new_lines.append("")

        if hint:
            new_lines.append('<details class="quiz-hint">')
            new_lines.append('<summary><strong>Show hint</strong></summary>')
            new_lines.append(f'<p>{esc(hint)}</p>')
            new_lines.append('</details>')
            new_lines.append("")

        if options:
            new_lines.extend([
                "<script>",
                "(() => {",
                f"  const quiz = document.getElementById('{quiz_name}');",
                "  if (!quiz) return;",
                "  const feedback = quiz.querySelector('.quiz-feedback');",
                "  const explanation = quiz.querySelector('.quiz-explanation');",
                "  quiz.querySelectorAll('.quiz-option-content[data-for]').forEach(content => {",
                "    content.addEventListener('click', () => {",
                "      const input = document.getElementById(content.dataset.for);",
                "      if (input.type === 'radio') input.checked = true;",
                "      else input.checked = !input.checked;",
                "    });",
                "  });",
                "  quiz.querySelector('.quiz-check').addEventListener('click', () => {",
                "    const inputs = [...quiz.querySelectorAll('input')];",
                "    const selected = inputs.filter(input => input.checked);",
                "    if (selected.length === 0) {",
                "      feedback.textContent = 'Please select an answer before checking.';",
                "      feedback.className = 'quiz-feedback quiz-unanswered';",
                "      explanation.hidden = true;",
                "      return;",
                "    }",
                "    const correct = inputs.every(input => input.checked === (input.dataset.correct === 'true'));",
                "    feedback.textContent = correct ? 'Correct.' : 'Not quite. Review your selection and try again.';",
                "    feedback.className = `quiz-feedback ${correct ? 'quiz-correct' : 'quiz-incorrect'}`;",
                "    quiz.querySelectorAll('.quiz-option').forEach(option => {",
                "      const input = option.querySelector('input');",
                "      const optionFeedback = option.querySelector('.quiz-option-feedback');",
                "      if (optionFeedback) optionFeedback.hidden = !input.checked;",
                "    });",
                "    explanation.hidden = false;",
                "  });",
                "  quiz.querySelector('.quiz-reset').addEventListener('click', () => {",
                "    quiz.querySelectorAll('input').forEach(input => { input.checked = false; });",
                "    feedback.textContent = '';",
                "    feedback.className = 'quiz-feedback';",
                "    explanation.hidden = true;",
                "    quiz.querySelectorAll('.quiz-option-feedback').forEach(item => { item.hidden = true; });",
                "  });",
                "})();",
                "</script>",
                "<style>",
                ".quiz-block { border: 1px solid #d9d9d9; border-radius: .4rem; padding: 1rem; margin: 1rem 0; }",
                ".quiz-option { border-radius: .25rem; margin: .5rem 0; padding: .35rem; }",
                ".quiz-option-control { align-items: flex-start; display: flex; gap: .6rem; }",
                ".quiz-option-control input { flex: 0 0 auto; margin-top: .35rem; }",
                ".quiz-option-content { cursor: pointer; flex: 1 1 auto; }",
                ".quiz-option-content > :last-child { margin-bottom: 0; }",
                ".quiz-option-feedback { background: #f5f5f5; border-left: .2rem solid #6c757d; margin: .5rem 0 0 1.5rem; padding: .5rem .75rem; }",
                ".quiz-actions { margin: 1rem 0 .5rem; }",
                ".quiz-feedback { font-weight: 600; min-height: 1.5em; }",
                ".quiz-correct { color: #137333; }",
                ".quiz-incorrect, .quiz-unanswered { color: #b3261e; }",
                ".quiz-explanation { border-left: .25rem solid #6c757d; margin-top: .75rem; padding-left: .75rem; }",
                ".quiz-hint { margin: .75rem 0 1rem; }",
                "</style>",
                "",
            ])
        count += 1

        if not found_end:
            click.echo(
                click.style(
                    "Warning: Quiz block has no END Quiz tag; "
                    "content continued to the end of the document.",
                    fg="yellow",
                )
            )

    if count > 0:
        click.echo(click.style("Detected quiz blocks", fg="blue"))
        click.echo(f"  Rendering {count} interactive quiz blocks")

    return "\n".join(new_lines), count
