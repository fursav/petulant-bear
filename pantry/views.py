from django.shortcuts import render, render_to_response, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django import forms
from django.db import connection, transaction, IntegrityError
from django.core import serializers
from django.template import RequestContext
import datetime
# Create your views here.

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30)
    password= forms.CharField(max_length=30, widget=forms.PasswordInput)

class CreateProductForm(forms.Form):
    product_name = forms.CharField(max_length= 100)
    cost = forms.DecimalField(decimal_places = 2)
    source = forms.CharField(max_length = 100)
	
######
class AddDropOffForm(forms.Form):
	cursor = connection.cursor()
	cursor.execute("SELECT ProductName FROM Product")
	names = cursor.fetchall()
	names = [(x[0],x[0]) for x in names]
	product_name = forms.ChoiceField(choices = names)
	quantity = forms.IntegerField()
	date = forms.DateField(initial=datetime.date.today())
########

class CreateClientForm(forms.Form):
	cursor = connection.cursor()
	cursor.execute("SELECT BagName FROM Bag")
	names = cursor.fetchall()
	names = [(x[0],x[0]) for x in names]

	first_name = forms.CharField(max_length= 100)
	last_name = forms.CharField(max_length= 100)
	phone = forms.CharField(max_length= 12)
	gender = forms.CharField(max_length= 6)
	DOB = forms.DateField() 
	start = forms.DateField()
	pDay = forms.IntegerField(31,1)
	apt = forms.CharField(max_length= 100)
	street = forms.CharField(max_length= 100)
	city = forms.CharField(max_length= 100)
	state = forms.CharField(max_length= 100)
	zip = forms.CharField(max_length= 100)
	bag_name = forms.ChoiceField(choices = names)

def index(request):
    if request.method == 'POST': # If the form has been submitted...
        form = LoginForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            cursor = connection.cursor()
            #check to see if the username password combination is stored in the db
            cursor.execute("SELECT Username, UserFName, UserLName From User WHERE Username = %s AND Password = %s", [username,password])
            u = cursor.fetchone()
            #print u
            if u is None:
                return render(request, 'pantry/index.html', {
                    'form': form,
                    'error_message':'Incorrect Username/Password combination'
                })
            name = u[1] + " " + u[2]
            
            request.session['username'] = u[0]
            request.session['user_name'] = name
            
            return HttpResponseRedirect(reverse('pantry:home'))
    else:
        form = LoginForm() # An unbound form

    return render(request, 'pantry/index.html', {
        'form': form,
    })

def home(request):
    
    return render(request, 'pantry/home.html')
    
def view_products(request,**kwargs):
    if request.is_ajax():
        q = request.GET.get('q')
        if q is not None:     
            cursor = connection.cursor()
            cursor.execute("""
                            SELECT * FROM QtyOnHand
                            WHERE ProductName
                            LIKE %s;
                           """,['%' + q + '%'])
            products = cursor.fetchall()
            return render_to_response('pantry/product_table.html',{ 'products':products },context_instance = RequestContext(request))

    cursor = connection.cursor()
    cursor.execute("""
                    CREATE VIEW if not exists DroppedOffQty AS 
                    SELECT Product.ProductName, Cost, SUM(Quantity) AS SQ
                    FROM Product
                    LEFT JOIN DropoffTransaction
                    ON Product.ProductName = DropoffTransaction.ProductName
                    GROUP BY Product.ProductName;
                   """)
    cursor.execute("""
                    CREATE VIEW if not exists pickup_bags as SELECT PickupTransaction.CID,BagName
                    FROM PickupTransaction 
                    JOIN Client 
                    ON PickupTransaction.CID 
                    WHERE PickupTransaction.CID = Client.CID;
                   """)
    cursor.execute("""
                    CREATE VIEW if not exists PickedUpQty AS SELECT ProductName, SUM(CurrentMnthQty) AS CMQ
                    FROM pickup_bags 
                    JOIN Holds 
                    ON pickup_bags.BagName = Holds.BagName 
                    GROUP BY ProductName;
                   """)
    cursor.execute("""
                    CREATE VIEW if not exists QtyOnHand AS
                    SELECT ProductName, ifnull(SQ,0)-ifnull(CMQ,0) AS QoH, Cost
                    FROM DroppedOffQty 
                    LEFT NATURAL JOIN PickedUpQty
                    GROUP BY ProductName;
                   """)
    cursor.execute("SELECT * FROM QtyOnHand")
    products = cursor.fetchall()
    return render(request, 'pantry/product_list.html',{
        'products':products
    })

def view_dropoffs(request):
	# if request.is_ajax():
        # q = request.GET.get('q')
        # if q is not None:     
            # cursor = connection.cursor()
            # cursor.execute("""
                            # SELECT Dropofftransaction.ProductName as Product, SourceName as Source, Quantity, Date
							# FROM DropoffTransaction
							# JOIN Product on Product.ProductName = DropoffTransaction.ProductName
                           # """,['%' + q + '%'])
            # dropoffs = cursor.fetchall()
            
            
            # #return HttpResponse(serializers.serialize("json", products))
            # return render_to_response('pantry/dropoff_list.html',{ 'dropoffs':dropoffs },context_instance = RequestContext(request))



    cursor = connection.cursor()
    cursor.execute("""
                    SELECT Dropofftransaction.ProductName, SourceName as Source, Quantity, Date
					FROM DropoffTransaction
					JOIN Product on Product.ProductName = DropoffTransaction.ProductName
                   """)
	#cursor.execute("SELECT * FROM DropoffTransaction")
    dropoffs = cursor.fetchall()
    return render(request, 'pantry/dropoff_list.html',{
        'dropoffs':dropoffs
    })
	#return render(request, 'pantry/dropoff_list.html')

def view_bags(request):

    cursor = connection.cursor()
    cursor.execute("""
                    CREATE VIEW if not exists bag_items AS
                    SELECT BagName, COUNT(*) AS Num_items  
                    FROM Holds GROUP BY BagName;
                   """)
    cursor.execute("""
                    CREATE VIEW if not exists bag_cost AS SELECT BagName, SUM(CurrentMnthQty*Cost) as Cost1 FROM Holds 
                    LEFT JOIN Product 
                    ON  Holds.ProductName = Product.ProductName 
                    GROUP BY BagName;
                   """)
    cursor.execute("""
                    CREATE VIEW if not exists bag_clients AS
                    SELECT BagName, COUNT(*) as Num_clients 
                    FROM Client 
                    GROUP BY BagName;
                   """)
    cursor.execute("""
                    SELECT bag_items.BagName, Num_items, ifnull(Num_clients,0), Cost1 
                    FROM bag_items 
                    JOIN bag_cost 
                    ON bag_items.BagName = bag_cost.BagName 
                    LEFT JOIN bag_clients 
                    ON bag_items.BagName = bag_clients.BagName;
                   """)
    #cursor.execute("SELECT * FROM QtyOnHand")
    bags = cursor.fetchall()
    return render(request, 'pantry/bag_list.html',{
        'bags':bags
    })

################################################## Hannah's work 

def add_dropoff(request):
	if request.method == 'POST': # If the form has been submitted...
		form = AddDropOffForm(request.POST) # A form bound to the POST data
		if form.is_valid(): # All validation rules pass
			product_name = form.cleaned_data['product_name']
			quantity = form.cleaned_data['quantity']
			date = form.cleaned_data['date']
			cursor = connection.cursor()
			cursor.execute("INSERT INTO DropOffTransaction(ProductName, Quantity, Date) VALUES (%s, %s, %s)", [product_name, quantity, date])
			transaction.commit_unless_managed()

			return HttpResponseRedirect(reverse('pantry:dropoff_list'))
	else:
		form = AddDropOffForm() # An unbound form
		return render(request, 'pantry/add_dropoff.html', {'form': form,})
###############################################################################

def create_product(request):
    if request.method == 'POST': # If the form has been submitted...
        form = CreateProductForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            product_name = form.cleaned_data['product_name']
            cost = form.cleaned_data['cost']
            source = form.cleaned_data['source']
            cursor = connection.cursor()
            
            try:
                cursor.execute("INSERT INTO Product VALUES (%s,%s,%s)", [product_name, cost, source])
            
                #need this line after altering database in django 1.5
                transaction.commit_unless_managed()
            except IntegrityError:
                return render(request, 'pantry/create_product.html', {'form': form, 'error_message':'Product already exists'})
            #return redirect('pantry:product_list', kwargs={"success_message":smsg})
            return HttpResponseRedirect(reverse('pantry:product_list'))
    else:
        form = CreateProductForm() # An unbound form
    return render(request, 'pantry/create_product.html', {'form': form,})

def view_clients(request):
	cursor = connection.cursor()
	cursor.execute("""
					SELECT CLName, CFName, Street || " " || City || ", " || State || " " || Zip as Address, CPhone, Start
					FROM Client
					""")
	clients = cursor.fetchall()
	return render(request, 'pantry/client_list.html', {'clients':clients})
	
def add_client(request):
	if request.method == 'POST': # If the form has been submitted...
		form = CreateClientForm(request.POST) # A form bound to the POST data
		if form.is_valid(): # All validation rules pass
			first_name = form.cleaned_data['first_name']
			last_name = form.cleaned_data['last_name']
			phone = form.cleaned_data['phone']
			gender = form.cleaned_data['gender']
			DOB = form.cleaned_data['DOB']
			start = form.cleaned_data['start']
			pDay = form.cleaned_data['pDay']
			apt = form.cleaned_data['apt']
			street = form.cleaned_data['street']
			city = form.cleaned_data['city']
			state = form.cleaned_data['state']
			zip = form.cleaned_data['zip']
			bag_name = form.cleaned_data['bag_name']
			cursor = connection.cursor()
            
			try:
				cursor.execute("SELECT CID FROM Client ORDER BY CID desc")
				topCID = cursor.fetchone()
				print topCID[0]
				cursor.execute("INSERT INTO Client VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", 
				[(topCID[0]+1), first_name, last_name, phone, gender, DOB, start, pDay, apt, street, city, state, zip, bag_name])
            
                #need this line after altering database in django 1.5
				transaction.commit_unless_managed()
			except IntegrityError:
				return render(request, 'pantry/add_client.html', {'form': form, 'error_message':'Client already exists'})
            #return redirect('pantry:product_list', kwargs={"success_message":smsg})
			return HttpResponseRedirect(reverse('pantry:client_list'))
	else:
		form = CreateClientForm() # An unbound form
	return render(request, 'pantry/add_client.html', {'form': form,})


    
