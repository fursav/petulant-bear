from django.conf.urls import patterns, url
from django.conf import settings
from pantry import views

urlpatterns = patterns('',
    url(r'^static(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ROOT_PATH }),
    url(r'^$', views.index, name='index'),
    url(r'^home/$', views.home, name='home'),
    url(r'^products/$', views.view_products, name='product_list'),
    url(r'^products/create_product/$', views.create_product, 
    name='create_product'),
    url(r'^dropoffs/$', views.view_dropoffs, name= 'dropoff_list'),
    url(r'^dropoffs/add_dropoff/$', views.add_dropoff, name='add_dropoff'),
    url(r'^bags/$', views.view_bags, name='bag_list'),
    url(r'^clients/$', views.view_clients, name= 'client_list'),
    url(r'^clients/add_client/$', views.add_client, name='add_client'),
    url(r'^clients/add_family/$', views.add_family_member, name='add_family'),
    url(r'^pickups/$', views.view_pickups, name= 'pickup_list'),
    url(r'^pickups/(?P<cid>\d+)/$', views.complete_pickup, name= 'complete_pickup'),
	url(r'^bags/(?P<BagName>[-\w\ ]+)/$', views.view_bag, name= 'bag_product_list'),
	url(r'^bags/(?P<BagName>[-\w\ ]+)/add_to_bag/$', views.add_to_bag, name= 'add_to_bag'),
	url(r'^bags/(?P<BagName>[-\w\ ]+)/edit_bag/$', views.edit_bag, name= 'edit_bag'),
	url(r'^reports/$', views.view_reports, name= 'reports'),
)
