from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django import forms
from django.db import connection
# Create your views here.

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30)
    password= forms.CharField(max_length=30, widget=forms.PasswordInput)

class CreateProductForm(forms.Form):
    product_name = forms.CharField(max_length= 100)
    cost = forms.DecimalField(decimal_places = 2)
    source = forms.CharField(max_length = 100)


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
    
def view_products(request):
    return render(request, 'pantry/product_list.html')

def view_dropoffs(request):
    return render(request, 'pantry/dropoff_list.html')

def add_dropoff(request):
    return

def create_product(request):
    if request.method == 'POST': # If the form has been submitted...
        form = CreateProductForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            product_name = form.cleaned_data['product_name']
            cost = form.cleaned_data['cost']
            source = form.cleaned_data['source']
            cursor = connection.cursor()
            cursor.execute("INSERT INTO Product VALUES (%s,%s,%s)", [product_name, cost, source])
            
            #need this line after altering database in django 1.5
            transaction.commit_unless_managed()

            return HttpResponseRedirect(reverse('pantry:product_list'))
    else:
        form = CreateProductForm() # An unbound form
    return render(request, 'pantry/create_product.html', {'form': form,})


    
