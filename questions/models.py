from django.db import models
from notes.models import Note

class Question(models.Model):
    MARK_CHOICES = [(1, "1 Mark"), (3, "3 Marks"), (8, "8 Marks")]
    MODE_CHOICES = [("mcq", "MCQ"), ("write", "Write Answer")]

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="questions")
    question = models.TextField()
    marks = models.PositiveSmallIntegerField(choices=MARK_CHOICES)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="write")
    options = models.JSONField(default=list, blank=True)
    correct_option = models.PositiveSmallIntegerField(null=True, blank=True)
    expected_components = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.marks} mark - {self.question[:60]}"
