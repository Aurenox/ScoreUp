from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from questions.models import Question
from notes.models import Note
from notes.gemini_service import generate_next_question_from_pdf
from .models import Attempt

@login_required
def answer(request, pk):
    question = get_object_or_404(Question, pk=pk, note__owner=request.user)
    ids = request.session.get("practice_question_ids", [])
    number = ids.index(question.id) + 1 if question.id in ids else len(ids) + 1
    return render(request, "practice/answer.html", {"question": question, "question_number": number})

@login_required
def submit_answer(request, pk):
    question = get_object_or_404(Question, pk=pk, note__owner=request.user)
    if request.method != "POST":
        return redirect("practice_answer", pk=pk)

    selected = request.POST.get("selected_option") or None
    is_correct = False
    correct_answer = None
    if question.mode == "mcq" and question.correct_option is not None:
        if question.options and question.correct_option < len(question.options):
            correct_answer = question.options[question.correct_option]
        try:
            is_correct = int(selected) == int(question.correct_option)
        except (TypeError, ValueError):
            is_correct = False

    attempt = Attempt.objects.create(
        user=request.user,
        question=question,
        answer_text=request.POST.get("answer_text", ""),
        selected_option=selected,
        drawing_data=request.POST.get("drawing_data", ""),
    )
    handwritten_pdf = request.FILES.get("handwritten_pdf")
    if handwritten_pdf:
        attempt.handwritten_pdf = handwritten_pdf
        attempt.save()

    if question.mode == "mcq":
        ids = request.session.get("practice_question_ids", [])
        return render(request, "practice/result.html", {
            "question": question, "attempt": attempt,
            "is_correct": is_correct, "correct_answer": correct_answer,
            "question_number": ids.index(question.id) + 1 if question.id in ids else 1,
        })

    if question.marks == 8 and attempt.handwritten_pdf:
        return redirect("evaluate_handwritten", attempt_id=attempt.pk)
    return redirect("evaluate_attempt", attempt_id=attempt.pk)

@login_required
def next_question(request):
    note_id = request.session.get("practice_note_id")
    marks = request.session.get("practice_marks")
    question_ids = request.session.get("practice_question_ids", [])
    if not note_id or not marks:
        return redirect("note_list")

    note = get_object_or_404(Note, pk=note_id, owner=request.user)
    previous = list(Question.objects.filter(id__in=question_ids).values_list("question", flat=True))
    mode = "mcq" if marks == 1 else "write"
    try:
        item = generate_next_question_from_pdf(note.pdf.path, marks, mode, previous)
        question = Question.objects.create(
            note=note, question=item["question"], marks=marks, mode=mode,
            options=item.get("options", []), correct_option=item.get("correct_option"),
            expected_components=item.get("expected_components", []),
        )
        question_ids.append(question.id)
        request.session["practice_question_ids"] = question_ids
        return redirect("practice_answer", pk=question.id)
    except Exception as exc:
        return render(request, "practice/answer.html", {"question": None, "error": str(exc)})

@login_required
def end_practice(request):
    request.session.pop("practice_note_id", None)
    request.session.pop("practice_marks", None)
    request.session.pop("practice_question_ids", None)
    return redirect("dashboard")
