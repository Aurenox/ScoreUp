from django.urls import path
from . import views

urlpatterns = [
    path("attempt/<int:attempt_id>/", views.evaluate_attempt, name="evaluate_attempt"),
    path("handwritten/<int:attempt_id>/", views.evaluate_handwritten, name="evaluate_handwritten"),
]
