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

		data=cartData(request)

		product_details = [{"identity": str(item['product']['id']), "name": item['product']['name'], "total_price": item['get_total']*100, "quantity": item['quantity'], "unit_price": item['product']['price']*100} for item in data['items']]

		print("product_details:", product_details)

		amount = data['order']['get_cart_total'] 
		amount = (amount // 1) * 100
		print(amount)
		csrf_token = csrf.get_token(request)

		url = 'https://a.khalti.com/api/v2/epayment/initiate/'
		payload = {
		"return_url": "http://127.0.0.1:8000/process_order/",
		"website_url": "http://127.0.0.1:8000/",
		"amount": amount + amount * .13,
		"purchase_order_id": "test12",
		"purchase_order_name": "test",
		"customer_info": {
			"name": name,
			"email": email,
			"phone": phone,
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
		print(response)
		payment_url = response.json()['payment_url']
		
		return HttpResponseRedirect(payment_url)

	return HttpResponse("Payment Failed")

def payment_success_callback(request):
	
	pidx = request.GET.get('pidx')
	amount = request.GET.get('amount')
	mobile = request.GET.get('mobile')
	purchase_order_id = request.GET.get('purchase_order_id')
	purchase_order_name = request.GET.get('purchase_order_name')
	transaction_id = request.GET.get('transaction_id')
	context={
	'pidx': pidx,
	'amount': amount,
	'mobile': mobile,
	'purchase_order_id': purchase_order_id,
	'purchase_order_name': purchase_order_name,
	'transaction_id': transaction_id,
	}

	return render(request, 'store/payment.html', context)
	

def processOrder(request):
	transaction_id = datetime.datetime.now().timestamp()
	data = json.loads(request.body)

	print(data)

	if request.user.is_authenticated:
		customer = request.user.customer
		order, created = Order.objects.get_or_create(customer=customer, complete=False)
	else:
		customer, order = guestOrder(request, data)

	total = float(data['form']['total'])
	order.transaction_id = transaction_id

	if total == order.get_cart_total:
		order.complete = True
	order.save()

	if order.shipping == True:
		ShippingAddress.objects.create(
		customer=customer,
		order=order,
		address=data['shipping']['address'],
		city=data['shipping']['city'],
		state=data['shipping']['state'],
		zipcode=data['shipping']['zipcode'],
		)

	return JsonResponse('Payment completed..', safe=False)


