from django.contrib.auth.decorators import login_required
from django.db import OperationalError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .exceptions import InvalidSearch, QueueFull
from .jobs import submit_job
from .models import SearchJob
from .openrouter import load_json

ERROR_MESSAGES = {
    "marketplace_unavailable": "Data marketplace belum tersedia. Silakan coba lagi nanti.",
    "provider_unavailable": "Pencarian cerdas sedang tidak tersedia. Coba lagi atau gunakan pencarian marketplace.",
    "invalid_search": "Permintaan belum dapat dipahami. Perjelas pencarian Anda.",
    "unsafe_search": "Permintaan memuat operasi yang tidak diizinkan.",
    "search_failed": "Pencarian belum dapat diselesaikan. Silakan coba lagi.",
}


@login_required(login_url="authentication:login")
@require_GET
def search(request):
    return render(request, "llm_searching/search.html")


@never_cache
@require_POST
def create_job(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "error_code": "login_required",
                "message": "Silakan masuk terlebih dahulu.",
            },
            status=401,
        )
    try:
        if request.content_type != "application/json" or len(request.body) > 12000:
            raise InvalidSearch("Kirim prompt sebagai JSON yang valid.")
        payload = load_json(request.body.decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"prompt"}:
            raise InvalidSearch("Kirim satu field prompt.")
        job = submit_job(request.user.pk, payload["prompt"])
    except (ValueError, UnicodeError, InvalidSearch) as exc:
        message = str(exc) if isinstance(exc, InvalidSearch) else "JSON tidak valid."
        return JsonResponse(
            {"error_code": "invalid_search", "message": message}, status=400
        )
    except QueueFull as exc:
        return JsonResponse({"error_code": exc.code, "message": str(exc)}, status=429)
    except OperationalError:
        return JsonResponse(
            {
                "error_code": "temporarily_unavailable",
                "message": "Pencarian sedang sibuk. Silakan coba lagi.",
            },
            status=503,
        )
    return JsonResponse(
        {
            "id": str(job.pk),
            "status": job.status,
            "status_url": reverse("llm_searching:job_status", args=[job.pk]),
        },
        status=202,
    )


@never_cache
@require_GET
def job_status(request, job_id):
    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "error_code": "login_required",
                "message": "Silakan masuk terlebih dahulu.",
            },
            status=401,
        )
    job = get_object_or_404(SearchJob, pk=job_id, owner_id=request.user.pk)
    result = dict(job.result)
    result.update(id=str(job.pk), status=job.status, error_code=job.error_code)
    if job.status == "failed":
        result["explanation"] = ERROR_MESSAGES.get(
            job.error_code, ERROR_MESSAGES["search_failed"]
        )
    return JsonResponse(result)
