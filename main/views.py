from django.shortcuts import render


def show_main(request):
    context = {
        'app_name': 'Urban Harvest Community',
    }
    return render(request, 'landing.html', context)

# Create your views here.
