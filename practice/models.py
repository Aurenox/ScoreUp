from django.conf import settings
from django.db import models
from questions.models import Question

class Attempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="attempts")
    answer_text = models.TextField(blank=True)
    drawing_data = models.TextField(blank=True)
    handwritten_pdf = models.FileField(upload_to="answers/", blank=True, null=True)
    selected_option = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.question.question[:50]}"
