from django.urls import path
from . import views

urlpatterns = [
    path("next/", views.next_question, name="next_question"),
    path("end/", views.end_practice, name="end_practice"),
    path("<int:pk>/", views.answer, name="practice_answer"),
    path("<int:pk>/submit/", views.submit_answer, name="submit_answer"),
]
