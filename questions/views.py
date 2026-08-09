from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from notes.models import Note
from notes.gemini_service import generate_next_question_from_pdf
from .models import Question

@login_required
def generate(request, note_id):
    note = get_object_or_404(Note, pk=note_id, owner=request.user)
    error = None
    if request.method == "POST":
        marks = int(request.POST.get("marks", "1"))
        mode = "mcq" if marks == 1 else "write"
        request.session["practice_note_id"] = note.id
        request.session["practice_marks"] = marks
        request.session["practice_question_ids"] = []
        try:
            item = generate_next_question_from_pdf(note.pdf.path, marks, mode, [])
            question = Question.objects.create(
                note=note, question=item["question"], marks=marks, mode=mode,
                options=item.get("options", []), correct_option=item.get("correct_option"),
                expected_components=item.get("expected_components", []),
            )
            request.session["practice_question_ids"] = [question.id]
            return redirect("practice_answer", pk=question.id)
        except Exception as exc:
            error = str(exc)
    return render(request, "questions/generate.html", {"note": note, "error": error})

@login_required
def question_detail(request, pk):
    question = get_object_or_404(Question, pk=pk, note__owner=request.user)
    return redirect("practice_answer", pk=question.pk)
