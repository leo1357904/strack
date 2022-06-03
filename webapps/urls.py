"""webapps URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
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
from strack import views

urlpatterns = [
    # Interpreter
    path('', views.interpreter_page, name='interpreter'),
    # TODO: ajax update. save the code, return the stack info and let the browser do the visualization
    # path('ajax/interpret', views.ajax_interpret, name='ajax_interpret'),

    # Basic pages and actions
    path('register', views.register_action, name='register'),
    path('login', views.login_action, name='login'),
    path('logout', views.logout_action, name='logout'),
    path('oauth/', include('social_django.urls', namespace='social')),
    path('oauth/profile-creation', views.oauth_profile_creation, name='oauth-profile'),

    # Profile
    path('profile/<int:id>', views.profile_page, name='profile'),
    path('follow/<int:id>', views.follow_action, name='follow'),
    path('unfollow/<int:id>', views.unfollow_action, name='unfollow'),
    path('photo/<int:id>', views.get_photo, name='photo'),
    path('profile/<int:pid>/star/<int:cid>', views.profile_star_action, name='profile-star'),
    path('profile/<int:pid>/unstar/<int:cid>', views.profile_unstar_action, name='profile-unstar'),
    path('profile/<int:pid>/delete/<int:cid>', views.profile_delete_code, name='profile-delete-code'),

    # Dashboard
    path('dashboard', views.dashboard_page, name='dashboard'),
    path('download/<int:id>', views.download_code, name='download'),

    #Code
    path('code/<int:id>', views.code_page, name='code'),
    path('star/<int:id>', views.star_action, name='star'),
    path('unstar/<int:id>', views.unstar_action, name='unstar'),
    path('code/<int:id>/star', views.code_page_star_action, name='code-page-star'),
    path('code/<int:id>/unstar', views.code_page_unstar_action, name='code-page-unstar'),
    path('init/add-anonymous-user', views.add_anonymous_user, name='init-add-anonymous'),
]
