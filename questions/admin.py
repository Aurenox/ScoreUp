from django.contrib import admin
from .models import Question

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("question", "marks", "mode", "note", "created_at")
    list_filter = ("marks", "mode")
