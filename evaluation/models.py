from django.db import models
from practice.models import Attempt

class Evaluation(models.Model):
    attempt = models.OneToOneField(Attempt, on_delete=models.CASCADE, related_name="evaluation")
    score = models.FloatField()
    max_score = models.PositiveSmallIntegerField()
    feedback = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.score}/{self.max_score}"
