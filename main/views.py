from django.shortcuts import render


def show_main(request):
    return render(request, 'index.html')

# Create your views here.
