from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django import forms
from django.db import connection
# Create your views here.

class LoginForm(forms.Form):
    username = forms.CharField(max_length=30)
    password= forms.CharField(max_length=30, widget=forms.PasswordInput)


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
    
