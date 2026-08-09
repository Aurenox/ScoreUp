from django.conf import settings
from django.db import models

class Note(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes")
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=150, default="General")
    module = models.CharField(max_length=150, default="Unit 1")
    pdf = models.FileField(upload_to="notes/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
