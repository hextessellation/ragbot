"""
URL configuration for ragchatbot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from chatapp import views
from django.shortcuts import redirect, render
from django.conf import settings
from django.conf.urls.static import static

def custom_404(request, exception):
    return render(request, '404.html', status=404)

handler404 = 'ragchatbot.urls.custom_404'  # Adjust if your project name is different

def redirect_to_login(request):
    return redirect('login')

urlpatterns = [
    path('', redirect_to_login, name='home'),
    # Keep the admin site
    path('admin/', admin.site.urls),
    
    # Add your app's URLs
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('documents/', views.document_list, name='documents'),
    path('upload/', views.upload_document, name='upload_document'),
    path('chat/<int:document_id>/', views.chat_view, name='chat'),
    #path('process-with-api/', views.process_with_api, name='process_with_api'),
    path('api-status/', views.api_status, name='api_status'),
    path('documents/<int:document_id>/reprocess/', views.reprocess_document, name='reprocess_document'),
    path('documents/<int:document_id>/debug/', views.debug_document, name='debug_document'),
    path('documents/<int:document_id>/delete/', views.delete_document, name='delete_document'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

