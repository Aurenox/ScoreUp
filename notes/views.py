from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Note

@login_required
def note_list(request):
    notes = Note.objects.filter(owner=request.user).order_by("-uploaded_at")
    return render(request, "notes/list.html", {"notes": notes})

@login_required
def upload_note(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        subject = request.POST.get("subject", "General").strip() or "General"
        module = request.POST.get("module", "Unit 1").strip() or "Unit 1"
        pdf = request.FILES.get("pdf")
        if not title or not pdf:
            return render(request, "notes/upload.html", {"error": "Title and PDF are required."})
        if not pdf.name.lower().endswith(".pdf"):
            return render(request, "notes/upload.html", {"error": "Only PDF files are allowed."})
        if pdf.size > 20 * 1024 * 1024:
            return render(request, "notes/upload.html", {"error": "PDF must be 20 MB or smaller."})
        note = Note.objects.create(owner=request.user, title=title, subject=subject, module=module, pdf=pdf)
        return redirect("note_detail", pk=note.pk)
    return render(request, "notes/upload.html")

@login_required
def note_detail(request, pk):
    note = get_object_or_404(Note, pk=pk, owner=request.user)
    return render(request, "notes/detail.html", {"note": note})

@login_required
def delete_note(request, pk):
    note = get_object_or_404(Note, pk=pk, owner=request.user)
    if request.method == "POST":
        note.pdf.delete(save=False)
        note.delete()
        return redirect("note_list")
    return render(request, "notes/detail.html", {"note": note})
