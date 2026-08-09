from django.urls import path
from . import views

urlpatterns = [
    path("generate/<int:note_id>/", views.generate, name="generate_questions"),
    path("<int:pk>/", views.question_detail, name="question_detail"),
]
