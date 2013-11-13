from django.conf.urls import patterns, url

from pantry import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^home/$', views.home, name='home'),
    url(r'^products/$', views.view_products, name='product_list'),
)
