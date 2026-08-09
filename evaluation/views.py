from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from practice.models import Attempt
from .models import Evaluation

from notes.gemini_service import (
    evaluate_text_answer,
    evaluate_text_answer_with_drawing,
    evaluate_handwritten_pdf,
)


@login_required
def evaluate_attempt(request, attempt_id):

    attempt = get_object_or_404(
        Attempt,
        pk=attempt_id,
        user=request.user
    )

    # --------------------------------------------------
    # Already evaluated?
    # --------------------------------------------------

    if hasattr(attempt, "evaluation"):
        evaluation = attempt.evaluation

        return render(
            request,
            "evaluation/result.html",
            {
                "attempt": attempt,
                "evaluation": evaluation,
            }
        )

    # --------------------------------------------------
    # 1 MARK MCQ
    # --------------------------------------------------

    if (
        attempt.question.marks == 1
        and attempt.question.mode == "mcq"
    ):

        selected = attempt.selected_option
        correct = attempt.question.correct_option

        try:
            ok = (
                selected is not None
                and correct is not None
                and int(selected) == int(correct)
            )
        except (ValueError, TypeError):
            ok = False

        data = {
            "score": 1 if ok else 0,

            "max_score": 1,

            "included": (
                ["Correct option selected."]
                if ok
                else []
            ),

            "missing": (
                []
                if ok
                else ["Select the correct option."]
            ),

            "strengths": (
                ["Correct answer."]
                if ok
                else []
            ),

            "improvements": (
                []
                if ok
                else ["Review the notes and retry."]
            ),

            "score_better": (
                []
                if ok
                else [
                    "Revise the relevant concept from your notes."
                ]
            ),

            "structure_feedback":
                "MCQ evaluation.",

            "diagram_feedback":
                "Not applicable.",
        }

    # --------------------------------------------------
    # 3 / 8 MARK WRITTEN ANSWER
    # --------------------------------------------------

    else:

        try:

            # IMPORTANT:
            # If the student drew a diagram,
            # send the drawing to Gemini too.

            if (
                attempt.question.marks == 8
                and attempt.drawing_data
            ):

                data = evaluate_text_answer_with_drawing(
                    notes_pdf_path=attempt.question.note.pdf.path,
                    question=attempt.question.question,
                    answer_text=attempt.answer_text,
                    drawing_data=attempt.drawing_data,
                    marks=attempt.question.marks,
                )

            else:

                data = evaluate_text_answer(
                    attempt.question.note.pdf.path,
                    attempt.question.question,
                    attempt.answer_text,
                    attempt.question.marks,
                )

        except Exception as exc:

            return render(
                request,
                "evaluation/result.html",
                {
                    "attempt": attempt,
                    "error": str(exc),
                }
            )

    # --------------------------------------------------
    # SAVE EVALUATION
    # --------------------------------------------------

    evaluation = Evaluation.objects.create(
        attempt=attempt,

        score=float(
            data.get("score", 0)
        ),

        max_score=int(
            data.get(
                "max_score",
                attempt.question.marks
            )
        ),

        feedback=data,
    )

    return render(
        request,
        "evaluation/result.html",
        {
            "attempt": attempt,
            "evaluation": evaluation,
        }
    )


# ======================================================
# HANDWRITTEN PDF EVALUATION
# ======================================================

@login_required
def evaluate_handwritten(request, attempt_id):

    attempt = get_object_or_404(
        Attempt,
        pk=attempt_id,
        user=request.user
    )

    # No PDF
    if not attempt.handwritten_pdf:

        return render(
            request,
            "evaluation/upload_handwritten.html",
            {
                "attempt": attempt,
                "error":
                    "Upload a handwritten PDF first."
            }
        )

    # Already evaluated
    if hasattr(attempt, "evaluation"):

        evaluation = attempt.evaluation

        return render(
            request,
            "evaluation/result.html",
            {
                "attempt": attempt,
                "evaluation": evaluation,
            }
        )

    # Evaluate handwritten PDF
    try:

        data = evaluate_handwritten_pdf(

            attempt.handwritten_pdf.path,

            attempt.question.note.pdf.path,

            attempt.question.question,

            8,
        )

    except Exception as exc:

        return render(
            request,
            "evaluation/result.html",
            {
                "attempt": attempt,
                "error": str(exc),
            }
        )

    # Save evaluation
    evaluation = Evaluation.objects.create(
        attempt=attempt,

        score=float(
            data.get("score", 0)
        ),

        max_score=8,

        feedback=data,
    )

    return render(
        request,
        "evaluation/result.html",
        {
            "attempt": attempt,
            "evaluation": evaluation,
        }
    )