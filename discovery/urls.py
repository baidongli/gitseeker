from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("search/", views.search, name="search"),
    path("explore/", views.explore, name="explore"),
    path("bookmarks/", views.bookmarks, name="bookmarks"),
    path("bookmark/<int:repo_id>/toggle/", views.toggle_bookmark, name="toggle_bookmark"),
    path("bookmark/<int:repo_id>/delete/", views.delete_bookmark, name="delete_bookmark"),
    path("repo/<str:owner>/<str:name>/", views.repo_detail, name="repo_detail"),
]
