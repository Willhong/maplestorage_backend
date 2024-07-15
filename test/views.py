# view.py

from django.http import HttpResponse


def sampleview(request):
    return HttpResponse(list)
