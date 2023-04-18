from django.urls import path

from . import views

urlpatterns = [
	#Leave as empty string for base url
	path('', views.store, name="store"),
	path('cart/', views.cart, name="cart"),
	path('checkout/', views.checkout, name="checkout"),
	path('update_item/', views.updateItem, name="update_item"),
	path('send_api_request',views.make_post_request_to_khalti,name="send_api_request"),
	path('process_order/', views.processOrder, name="process_order"),

]