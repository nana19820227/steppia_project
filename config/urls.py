from django.contrib import admin
from django.urls import path, include  # <--- ★ここが重要！ ', include' が必要です

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('steppia_app.urls')),
]
