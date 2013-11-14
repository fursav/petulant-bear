from django.conf.urls import patterns, url

from pantry import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^home/$', views.home, name='home'),
    url(r'^products/$', views.view_products, name='product_list'),
    url(r'^products/create_product/$', views.create_product,   
    name='create_product'),
    url(r'^dropoffs/$', views.view_dropoffs, name= 'dropoff_list'),
    url(r'^dropoffs/add_dropoff/$', views.add_dropoff, name= 
   'add_dropoff'),
)
