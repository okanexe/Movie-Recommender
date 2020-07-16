from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name = 'blog-home'),
    # path('about/', views.fetchdb, name = 'blog-about'),
    path('simple_upload.html/', views.simple_upload, name = 'blog-simple_upload'),
    # path('analysis.html/', views.profile_upload, name = 'blog-analysis'),
    path('reading.html/', views.analysis, name = 'blog-reading'),
    path('about.html/', views.fileUpload, name ='blog-about'),
]