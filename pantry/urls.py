from django.conf.urls import patterns, url

from pantry import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^(?P<username>\w+)/home/$', views.home, name='home'),
)
