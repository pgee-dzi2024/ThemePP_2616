from django.shortcuts import render

def index(request):
    return render(request, 'main/index.html')


def campaign_create_page(request):
    return render(request, 'main/campaign_create.html')


def campaign_detail_page(request, pk):
    return render(request, 'main/campaign_detail.html', {'pk': pk})
