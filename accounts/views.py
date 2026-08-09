from collections import defaultdict
from io import BytesIO
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import FileResponse
from django.shortcuts import redirect, render
from practice.models import Attempt
from evaluation.models import Evaluation

def home(request):
    return redirect("dashboard") if request.user.is_authenticated else render(request, "home.html")

def register(request):
    if request.user.is_authenticated: return redirect("dashboard")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(); login(request, user); return redirect("dashboard")
    return render(request, "accounts/register.html", {"form": form})

@login_required
def dashboard(request):
    attempts = Attempt.objects.filter(user=request.user).select_related("question__note")
    stats = {}
    for marks in (1,3,8):
        qs = attempts.filter(question__marks=marks)
        if marks == 1:
            correct = sum(1 for a in qs if a.selected_option is not None and a.question.correct_option is not None and int(a.selected_option)==int(a.question.correct_option))
            stats[marks] = {"attempted":qs.count(),"scored":correct,"max":qs.count(),"percent":round(correct/qs.count()*100,1) if qs.count() else 0}
        else:
            evs = Evaluation.objects.filter(attempt__in=qs)
            score = sum(e.score for e in evs); maximum = sum(e.max_score for e in evs)
            stats[marks] = {"attempted":qs.count(),"scored":round(score,2),"max":maximum,"percent":round(score/maximum*100,1) if maximum else 0}
    subjects=defaultdict(lambda:{1:[0,0],3:[0,0],8:[0,0]}); modules=defaultdict(lambda:{1:[0,0],3:[0,0],8:[0,0]})
    for a in attempts:
        m=a.question.marks
        if m==1:
            s=1 if a.selected_option is not None and a.question.correct_option is not None and int(a.selected_option)==int(a.question.correct_option) else 0; mx=1
        else:
            try: ev=a.evaluation; s,mx=ev.score,ev.max_score
            except Evaluation.DoesNotExist: continue
        for d,key in ((subjects,a.question.note.subject),(modules,f"{a.question.note.subject} — {a.question.note.module}")):
            d[key][m][0]+=s; d[key][m][1]+=mx
    subject_rows=[]
    for k,v in subjects.items():
        subject_rows.append({"subject":k,**{f"m{m}":round(v[m][0]/v[m][1]*100,1) if v[m][1] else 0 for m in (1,3,8)}})
    module_rows=[]
    for k,v in modules.items():
        module_rows.append({"module":k,**{f"m{m}":round(v[m][0]/v[m][1]*100,1) if v[m][1] else 0 for m in (1,3,8)}})
    return render(request,"accounts/dashboard.html",{"stats":stats,"subject_rows":subject_rows,"module_rows":module_rows})

def _rows(user, marks):
    qs=Attempt.objects.filter(user=user,question__marks=marks).select_related("question__note").order_by("created_at")
    out=[]
    for a in qs:
        if marks==1:
            score=1 if a.selected_option is not None and a.question.correct_option is not None and int(a.selected_option)==int(a.question.correct_option) else 0
            ans=a.question.options[int(a.selected_option)] if a.selected_option is not None and a.question.options and int(a.selected_option)<len(a.question.options) else "Not answered"
            correct=a.question.options[a.question.correct_option] if a.question.options and a.question.correct_option is not None else ""
            out.append((a,score,1,ans,correct))
        else:
            try: ev=a.evaluation; out.append((a,ev.score,ev.max_score,a.answer_text or ("Handwritten PDF submitted" if a.handwritten_pdf else ""),"; ".join(ev.feedback.get("score_better",[]))))
            except Evaluation.DoesNotExist: out.append((a,0,marks,a.answer_text,""))
    return out

@login_required
def download_report(request, marks):
    if marks not in (1,3,8): return redirect("dashboard")
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    rows=_rows(request.user,marks); buf=BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=12*mm,rightMargin=12*mm,topMargin=12*mm,bottomMargin=12*mm); st=getSampleStyleSheet(); story=[Paragraph(f"ScoreUp — {marks}-Mark Practice Report",st["Title"]),Spacer(1,10)]
    total=sum(float(r[1]) for r in rows); maximum=sum(float(r[2]) for r in rows); story.append(Paragraph(f"Attempted: {len(rows)} &nbsp;&nbsp; Score: {total:g}/{maximum:g}",st["Heading2"])); story.append(Spacer(1,10))
    for i,(a,score,mx,ans,correct) in enumerate(rows,1):
        story += [Paragraph(f"{i}. {a.question.question}",st["Heading3"]),Paragraph(f"Answer: {ans or 'No answer'}",st["BodyText"]),Paragraph(f"Score: {score:g}/{mx:g}",st["BodyText"])]
        if correct: story.append(Paragraph(f"Correct / improvement: {correct}",st["BodyText"]))
        story.append(Spacer(1,10))
    doc.build(story); buf.seek(0)
    return FileResponse(buf,as_attachment=True,filename=f"scoreup_{marks}_mark_report.pdf",content_type="application/pdf")
