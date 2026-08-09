import base64
import json
import re
from pathlib import Path

from django.conf import settings
from google import genai
from google.genai import types


# =========================================================
# GEMINI CLIENT
# =========================================================

def get_client():
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to your .env file."
        )

    return genai.Client(
        api_key=settings.GEMINI_API_KEY
    )


# =========================================================
# PDF UPLOAD
# =========================================================

def upload_pdf(pdf_path):
    client = get_client()

    return client.files.upload(
        file=str(Path(pdf_path))
    )


# =========================================================
# JSON PARSER
# =========================================================

def _parse_json(text):
    text = text.strip()

    # Remove ```json
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove ```
    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Gemini returned invalid JSON: {text[:1200]}"
        ) from exc


# =========================================================
# GENERATE FIRST QUESTIONS
# =========================================================

def generate_questions_from_pdf(
    pdf_path,
    marks,
    mode="mcq"
):
    client = get_client()

    uploaded = upload_pdf(pdf_path)

    if marks == 1 and mode == "mcq":

        instruction = """
Create 5 one-mark MCQs.

Each question must have exactly 4 options.

Return ONLY valid JSON:

[
    {
        "question": "...",
        "options": ["A", "B", "C", "D"],
        "correct_option": 0
    }
]

correct_option must be 0, 1, 2, or 3.
"""

    elif marks == 1:

        instruction = """
Create 5 one-mark short-answer questions.

Return ONLY valid JSON:

[
    {
        "question": "..."
    }
]
"""

    elif marks == 3:

        instruction = """
Create 5 three-mark short-answer questions.

Return ONLY valid JSON:

[
    {
        "question": "..."
    }
]
"""

    else:

        instruction = """
Create 5 university-style eight-mark questions.

Return ONLY valid JSON:

[
    {
        "question": "...",
        "expected_components": [
            "definition/introduction",
            "key points",
            "example or application",
            "diagram/flowchart if relevant",
            "conclusion"
        ]
    }
]

Do not force a diagram when it is not relevant.
"""

    prompt = f"""
You are ScoreUp, an exam preparation assistant.

Use ONLY the uploaded study notes as the source.

Do not invent facts outside the notes.

Select important and exam-relevant concepts.

The requested question value is {marks} mark(s).

{instruction}

Important:

- Do not include answers except correct_option for MCQs.
- Keep questions clear.
- Make them suitable for university students.
- Avoid duplicate questions.
- Output JSON only.
- No markdown fences.
"""

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[
            uploaded,
            prompt
        ],
    )

    return _parse_json(
        response.text
    )


# =========================================================
# EVALUATE TEXT ANSWER
# =========================================================

def evaluate_text_answer(
    pdf_path,
    question,
    answer_text,
    marks
):
    client = get_client()

    uploaded = upload_pdf(
        pdf_path
    )

    rubric = f"""
You are ScoreUp, an AI university exam-answer evaluator.

Evaluate the student's answer for this
{marks}-mark question.

QUESTION:
{question}

STUDENT ANSWER:
{answer_text}

Use the uploaded study notes as the
primary reference.

Return ONLY valid JSON:

{{
    "score": 0,
    "max_score": {marks},

    "included": [
        "..."
    ],

    "missing": [
        "..."
    ],

    "strengths": [
        "..."
    ],

    "improvements": [
        "..."
    ],

    "score_better": [
        "..."
    ],

    "structure_feedback": "...",

    "diagram_feedback": "..."
}}

Evaluate:

- correctness
- important points
- completeness
- technical accuracy
- answer structure
- examples where relevant
- diagram requirement where relevant
- conclusion where relevant

Score fairly.

Do not guarantee marks.

Mention that the score is an AI estimate.

For score_better, give concrete things
the student can add or improve.
"""

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[
            uploaded,
            rubric
        ],
    )

    return _parse_json(
        response.text
    )


# =========================================================
# EVALUATE 8-MARK TEXT + DRAWING
# =========================================================

def evaluate_text_answer_with_drawing(
    notes_pdf_path,
    question,
    answer_text,
    drawing_data,
    marks
):
    """
    Evaluates:

    1. Student's text answer
    2. Student's hand-drawn diagram

    Used mainly for 8-mark questions.
    """

    client = get_client()

    # -----------------------------------------------------
    # Upload study notes
    # -----------------------------------------------------

    notes_file = upload_pdf(
        notes_pdf_path
    )

    # -----------------------------------------------------
    # Convert canvas Base64 → image
    # -----------------------------------------------------

    if not drawing_data:
        raise ValueError(
            "No drawing data was submitted."
        )

    try:

        if "," in drawing_data:

            header, encoded = (
                drawing_data.split(
                    ",",
                    1
                )
            )

        else:

            encoded = drawing_data

        image_bytes = base64.b64decode(
            encoded
        )

    except Exception as exc:

        raise ValueError(
            "Unable to process the submitted diagram."
        ) from exc

    # -----------------------------------------------------
    # Gemini prompt
    # -----------------------------------------------------

    prompt = f"""
You are ScoreUp, an AI university exam evaluator.

Evaluate this student's {marks}-mark answer.

REFERENCE:
The uploaded PDF contains the student's study notes.

QUESTION:
{question}

STUDENT TEXT ANSWER:
{answer_text}

A diagram/flowchart created by the student
is also provided as an image.

IMPORTANT:
You MUST inspect the diagram image.

Do NOT say the diagram is missing because
an image is provided.

Evaluate the text answer AND the diagram together.

For an 8-mark answer check:

1. Definition/introduction
2. Main concepts
3. Technical correctness
4. Important points
5. Examples/applications where relevant
6. Answer structure
7. Diagram correctness
8. Diagram relevance
9. Diagram labels
10. Arrows and relationships
11. Overall completeness

If the question does not require a diagram,
do not unnecessarily penalize the student.

Give realistic university-style marks.

Return ONLY valid JSON:

{{
    "score": 0,
    "max_score": {marks},

    "included": [
        "..."
    ],

    "missing": [
        "..."
    ],

    "strengths": [
        "..."
    ],

    "improvements": [
        "..."
    ],

    "score_better": [
        "..."
    ],

    "structure_feedback": "...",

    "diagram_feedback": "..."
}}

For diagram_feedback:

- Explain what the student drew correctly.
- Identify incorrect/missing components.
- Mention missing labels or arrows.
- Suggest how to make the diagram better.
- Never say the diagram is missing when it is provided.

The score is an AI estimate, not a guaranteed examiner mark.
"""

    # -----------------------------------------------------
    # Send PDF + prompt + drawing image
    # -----------------------------------------------------

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/png"
    )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[
            notes_file,
            prompt,
            image_part
        ],
    )

    return _parse_json(
        response.text
    )


# =========================================================
# HANDWRITTEN 8-MARK PDF
# =========================================================

def evaluate_handwritten_pdf(
    answer_pdf_path,
    notes_pdf_path,
    question,
    marks=8
):
    client = get_client()

    notes_file = upload_pdf(
        notes_pdf_path
    )

    answer_file = upload_pdf(
        answer_pdf_path
    )

    prompt = f"""
You are evaluating a handwritten university
exam answer for ScoreUp.

REFERENCE STUDY NOTES:
Provided as one PDF.

STUDENT HANDWRITTEN ANSWER:
Provided as another PDF.

QUESTION:
{question}

MARKS:
{marks}

Evaluate ONLY the student's submitted answer
against the question and reference notes.

Return ONLY valid JSON:

{{
    "score": 0,
    "max_score": 8,

    "included": [
        "..."
    ],

    "missing": [
        "..."
    ],

    "strengths": [
        "..."
    ],

    "improvements": [
        "..."
    ],

    "score_better": [
        "..."
    ],

    "structure_feedback": "...",

    "diagram_feedback": "...",

    "handwriting_readability": "..."
}}

Check:

- correctness
- important points
- answer structure
- examples where relevant
- diagrams/flowcharts where relevant
- conclusion where relevant
- completeness
- handwriting readability

The score is an AI estimate,
not a guaranteed examiner mark.
"""

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[
            notes_file,
            answer_file,
            prompt
        ],
    )

    return _parse_json(
        response.text
    )


# =========================================================
# GENERATE ONE NEW QUESTION
# =========================================================

def generate_next_question_from_pdf(
    pdf_path,
    marks,
    mode,
    previous_questions=None
):
    client = get_client()

    uploaded = upload_pdf(
        pdf_path
    )

    previous_questions = (
        previous_questions or []
    )

    # -----------------------------------------------------
    # Question type
    # -----------------------------------------------------

    if marks == 1:

        instruction = """
Generate ONE 1-mark MCQ.

Exactly 4 options.

Exactly one correct option.

Return ONLY JSON:

{
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "correct_option": 0
}

correct_option must be 0, 1, 2 or 3.
"""

    elif marks == 3:

        instruction = """
Generate ONE 3-mark university-level
short-answer question.

Return ONLY JSON:

{
    "question": "...",
    "expected_components": [
        "point 1",
        "point 2",
        "point 3"
    ]
}
"""

    else:

        instruction = """
Generate ONE 8-mark university-level
long-answer question.

Where relevant, expect:

- definition
- explanation
- key points
- example
- diagram/flowchart
- conclusion

Return ONLY JSON:

{
    "question": "...",
    "expected_components": [
        "component 1",
        "component 2",
        "component 3"
    ]
}

Do not force a diagram when it is not relevant.
"""

    # -----------------------------------------------------
    # Previous questions
    # -----------------------------------------------------

    previous = "\n".join(
        f"- {q}"
        for q in previous_questions[-100:]
    )

    if not previous:
        previous = "None yet."

    # -----------------------------------------------------
    # Prompt
    # -----------------------------------------------------

    prompt = f"""
You are ScoreUp, an exam preparation assistant.

Use ONLY the uploaded study notes.

Generate exactly ONE new question
worth {marks} mark(s).

Do not repeat or closely duplicate
previous questions.

Prefer a different concept when possible.

Do not invent facts.

PREVIOUS QUESTIONS:

{previous}

{instruction}

Return JSON only.

No markdown.
"""

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[
            uploaded,
            prompt
        ],
    )

    return _parse_json(
        response.text
    )