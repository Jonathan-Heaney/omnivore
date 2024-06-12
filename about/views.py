from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def how_it_works(request):
    return render(request, 'about/how_it_works.html')


def faq(request):
    return render(request, 'about/faq.html')


@login_required(login_url="/login")
def submission_guidelines(request):
    return render(request, 'about/submission_guidelines.html')
