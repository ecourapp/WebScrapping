from django.urls import path

from scrapper import views

app_name = "scrapper"

urlpatterns = [
    path('scrapper', views.scrapper, name="scrapper"),
    path('top', views.top_movies, name="top"),
    path('latest', views.latest_movies, name="latest"),
    path('single', views.single, name="single"),
    path('', views.home, name="home"),
]
