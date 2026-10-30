from django.urls import path

from . import views

app_name = "llm_searching"
urlpatterns = [
    path("", views.search, name="search"),
    path("api/jobs/", views.create_job, name="create_job"),
    path("api/jobs/<uuid:job_id>/", views.job_status, name="job_status"),
]
