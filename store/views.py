from django.shortcuts import render
from django.http import JsonResponse
import json
import datetime
from .models import * 
from .utils import cookieCart, cartData, guestOrder


from django.http import HttpResponse
from django.middleware import csrf
from django.http import HttpResponseRedirect
import requests
import urllib
from urllib.parse import urlparse, parse_qs

def store(request):
	data = cartData(request)

	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	products = Product.objects.all()
	context = {'products':products, 'cartItems':cartItems}
	return render(request, 'store/store.html', context)


def cart(request):
	data = cartData(request)

	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	context = {'items':items, 'order':order, 'cartItems':cartItems}
	return render(request, 'store/cart.html', context)

def checkout(request):
	data = cartData(request)
	
	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	context = {'items':items, 'order':order, 'cartItems':cartItems}
	return render(request, 'store/checkout.html', context)

def updateItem(request):
	data = json.loads(request.body)
	productId = data['productId']
	action = data['action']
	print('Action:', action)
	print('Product:', productId)

	customer = request.user.customer
	product = Product.objects.get(id=productId)
	order, created = Order.objects.get_or_create(customer=customer, complete=False)

	orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

	if action == 'add':
		orderItem.quantity = (orderItem.quantity + 1)
	elif action == 'remove':
		orderItem.quantity = (orderItem.quantity - 1)

	orderItem.save()

	if orderItem.quantity <= 0:
		orderItem.delete()

	return JsonResponse('Item was added', safe=False)

def make_post_request_to_khalti(request):
	if request.method == "POST":
		name = request.POST.get("name")
		email = request.POST.get("email")
		phone = request.POST.get("phone")
		total = request.POST.get('total')
		address = request.POST.get("address")
		city = request.POST.get("city")
		state = request.POST.get("state")
		zipcode = request.POST.get("zipcode")
		country = request.POST.get("country")
		if(not(address and city and city and state and zipcode and country)):
			return_url = "http://127.0.0.1:8000/process_order/?name={}&email={}&phone={}&total={}".format(
				urllib.parse.quote(name), 
				urllib.parse.quote(email), 
				urllib.parse.quote(phone),
				urllib.parse.quote(total),
			)
		else:
			return_url = "http://127.0.0.1:8000/process_order/?name={}&email={}&phone={}&total={}&address={}&city={}&state={}&zipcode={}&country={}".format(
				urllib.parse.quote(name), 
				urllib.parse.quote(email), 
				urllib.parse.quote(phone),
				urllib.parse.quote(total),
				urllib.parse.quote(address), 
				urllib.parse.quote(city), 
				urllib.parse.quote(state), 
				urllib.parse.quote(zipcode), 
				urllib.parse.quote(country),
			)	
	
		data=cartData(request)
		print(data)
		product_details = [{"identity": str(item['product']['id']), "name": item['product']['name'], "total_price": (item['get_total']//1)*100, "quantity": item['quantity'], "unit_price": (item['product']['price']//1)*100} for item in data['items']]

		
		print("product_details:", product_details)

		amount = data['order']['get_cart_total'] 
		amount = (amount // 1) * 100
		csrf_token = csrf.get_token(request)

		url = 'https://a.khalti.com/api/v2/epayment/initiate/'
		payload = {
		"return_url": return_url,
		"website_url": "http://127.0.0.1:8000/",
		"amount": amount + amount * .13,
		"purchase_order_id": "test12",
		"purchase_order_name": "test",
		"customer_info":{
			"name": name,
			"email":email,
			"phone":phone,
		},
		"amount_breakdown": [
			{
				"label": "Mark Price",
				"amount": amount
			},
			{
				"label": "VAT",
				"amount": amount * .13
			}
		],
		"product_details": product_details
		}

		headers = {
			'Content-Type': 'application/json',
			"Authorization": "key 84a068d414ff4a189e1dbae85a09c9a3",
			'X-CSRFToken': csrf_token,  
		}

		response = requests.post(url, json=payload, headers=headers)
		print(response.json())
		if("payment_url" in response.json()):
			payment_url = response.json()['payment_url']
			return HttpResponseRedirect(payment_url)
		elif("error_key" in response.json()):
			return render(request, 'store/error.html', {'messages': response.json()})	
		else:
			return render(request, 'store/error.html', {'messages': response.json()})

			
		
		

	return HttpResponse("Payment Failed")

	

def processOrder(request):
	name = request.GET.get('name')
	email = request.GET.get('email')
	phone = request.GET.get('phone')
	address = request.GET.get('address')
	city = request.GET.get('city')
	state = request.GET.get('state')
	zipcode = request.GET.get('zipcode')
	transaction_id = request.GET.get('transaction_id')


	query_string = request.GET.get('country')		

	if(query_string):
		# Extract country and pidx
		country = query_string.split('?')[0]
		pidx=query_string.split('?')[1]
		pidx = pidx.split('=')[1]
		total = float(request.GET.get('total'))	
	else:
		total = request.GET.get('total')
		pidx= total.split('?')[1]
		pidx = pidx.split('=')[1]
		total = float(total.split('?')[0])



	# payment verification look up
	csrf_token = csrf.get_token(request)
	url = "https://a.khalti.com/api/v2/epayment/lookup/"
	request_data = {
		'pidx':pidx,
	}
	headers = {
			'Content-Type': 'application/json',
			"Authorization": "key 84a068d414ff4a189e1dbae85a09c9a3",
			'X-CSRFToken': csrf_token,  
	}
	response = requests.post(url, json=request_data,headers=headers)
	response=response.json()

	if response.get('status_code') == 401:
		# Invalid Authorization key
		return render(request, 'store/error.html', {'message': 'Invalid Authorization key'})

	if response.get('error_key') == 'validation_error':
		# Invalid payment_id
		return render(request, 'store/error.html', {'message': 'Invalid payment_id'})


	context={
			'name':name,
			'email':email,
			'total':total,
			'transaction_id':transaction_id,
			'response':response,
	}

	if request.user.is_authenticated:
		customer = request.user.customer
		order, created = Order.objects.get_or_create(customer=customer, complete=False)
	else:
		customer, order = guestOrder(request, name,email)

	order.transaction_id = transaction_id

	if total == order.get_cart_total:
		order.complete = True
		order.save()
		print("inside total condition")
		if order.shipping == True:
			print("inside shipping condition")
			ShippingAddress.objects.create(
			customer=customer,
			order=order,
			address=address,
			city=city,
			state=state,
			zipcode=zipcode,
			)

		
		return render(request, 'store/payment_status.html', context)

	else:
		return render(request, 'store/payment_status.html', context)

	

	return render(request, 'store/home.html')


