from django.shortcuts import render, render_to_response, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django import forms
from django.db import connection, transaction, IntegrityError
from django.core import serializers
from django.template import RequestContext
from django.forms.formsets import formset_factory
import datetime, calendar
# Create your views here.
#client_reference_id = -1



class LoginForm(forms.Form):
    username = forms.CharField(max_length=30)
    password= forms.CharField(max_length=30, widget=forms.PasswordInput)

class CreateProductForm(forms.Form):
    product_name = forms.CharField(max_length= 100)
    cost = forms.DecimalField(decimal_places = 2)
    source = forms.CharField(max_length = 100)
	

class AddDropOffForm(forms.Form):

    def __init__(self, *args, **kwargs):
        cursor = connection.cursor()
        cursor.execute("SELECT ProductName FROM Product ORDER BY ProductName")
        names = cursor.fetchall()
        names = [(x[0],x[0]) for x in names]
        super(AddDropOffForm, self).__init__(*args, **kwargs)
        self.fields['product_name'] = forms.ChoiceField(
            choices=names )
    product_name = forms.ChoiceField(choices = [])
    quantity = forms.IntegerField(1000,1)
    date = forms.DateField(initial=datetime.date.today())
    

class AddToBagForm(forms.Form):

    def __init__(self, *args, **kwargs):
        cursor = connection.cursor()
        try:
            cursor.execute("""
                            SELECT ProductName 
                            FROM Product
                            WHERE ProductName 
                            NOT IN (
                                SELECT ProductName 
                                FROM Holds 
                                WHERE BagName= %s)
                                """,[kwargs['initial']['BagName']])
        except:
            cursor.execute("""
                            SELECT ProductName 
                            FROM Product
                            """)
        names = cursor.fetchall()
        names = [(x[0],x[0]) for x in names]
        super(AddToBagForm, self).__init__(*args, **kwargs)
        self.fields['product_name'] = forms.ChoiceField(
            choices=names )
    product_name = forms.ChoiceField(choices = [])
    quantity = forms.IntegerField(1000,1)
    


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
	
class AddFamilyMemberForm(forms.Form):
	first_name = forms.CharField(max_length= 100)
	last_name = forms.CharField(max_length= 100)
	gender = forms.CharField(max_length= 12)
	DOB = forms.DateField() 

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
    stats = {'Most requested products':[],'Most expensive products':[],
             'Most used sources':[],'Most in stock products':[]}
    cursor = connection.cursor()
    cursor.execute("""
                    SELECT ProductName, SUM(CurrentMnthQty) 
                    FROM Holds 
                    GROUP by ProductName
                    ORDER by SUM(CurrentMnthQty) DESC
                    """)
    for i in range(5):        
        stats["Most requested products"].append(cursor.fetchone())
    cursor.execute("""
                    SELECT ProductName, Cost
                    FROM Product 
                    ORDER BY Cost DESC
                    """)
    for i in range(5):        
        stats["Most expensive products"].append(cursor.fetchone())
    cursor.execute("""
                    SELECT SourceName, Sum(Quantity)
                    FROM Product
                    NATURAL JOIN DropOffTransaction
                    GROUP BY SourceName
                    ORDER BY SUM(Quantity) DESC
                    """)
    for i in range(5):        
        stats["Most used sources"].append(cursor.fetchone())
        
    cursor.execute("""
                    SELECT ProductName, QoH
                    FROM QtyOnHand
                    ORDER BY QoH DESC
                    """)
    for i in range(5):        
        stats["Most in stock products"].append(cursor.fetchone())
    return render(request, 'pantry/home.html',{'stats':stats,})
    
def view_products(request):
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
					WHERE strftime('%m','2013-11-01') = strftime('%m', Date);
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

def view_bag(request, BagName):
	cursor = connection.cursor()
	cursor.execute("""
					SELECT ProductName, CurrentMnthQty as Quantity
					FROM Holds 
					WHERE BagName = %s
					""",[BagName])
	bag = cursor.fetchall()
	
	#only allow editing at the end of the month
	disabled = False
	#d = datetime.date.today()
	#if d.day != calendar.monthrange(d.year,d.month)[1]:
	#    disabled = True
	return render(request, 'pantry/bag.html', {'bag':bag, 'BagName':BagName, 'disabled':disabled})
	
def edit_bag(request, BagName):
    if request.method == 'POST':
        params = request.POST
        
        #update last month qty
        cursor = connection.cursor()
        cursor.execute("""
	                    UPDATE Holds
	                    SET LastMnthQty = (SELECT CurrentMnthQty FROM Holds WHERE BagName = %s)
	                    WHERE BagName = %s
	                    """, [BagName,BagName])
        transaction.commit_unless_managed()
        #update current month qty
        for k,v in params.iteritems():
            if k.startswith('qty_'):
                pname= k[4:]
                cursor.execute("""
					        UPDATE Holds
    	                    SET CurrentMnthQty = %s
    		                WHERE BagName = %s
    		                AND ProductName = %s
					        """,[v,BagName,pname])
                transaction.commit_unless_managed()
                
                
        #delete products
        removed_products = params.getlist("remove_product")
        for pname in removed_products:
            print pname
            cursor = connection.cursor()
            cursor.execute("""
					        DELETE FROM Holds
					        WHERE BagName = %s
					        AND ProductName = %s
					        """,[BagName,pname])
            transaction.commit_unless_managed()
            
        return redirect('pantry:bag_product_list',BagName=BagName)
    else:
        #ass
        #print request
	    cursor = connection.cursor()
	    cursor.execute("""
					    SELECT ProductName, CurrentMnthQty as Quantity, LastMnthQty
					    FROM Holds 
					    WHERE BagName = %s
					    """,[BagName])
	    bag = cursor.fetchall()
	    
	    #formset = AddFormSet()
    return render(request, 'pantry/edit_bag.html', {'bag':bag, 'BagName':BagName})

def add_to_bag(request,BagName):
    if request.method == 'POST': # If the form has been submitted...
        form = AddToBagForm(request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            product_name = form.cleaned_data['product_name']
            quantity = form.cleaned_data['quantity']
            cursor = connection.cursor()
            cursor.execute("""
                            INSERT INTO Holds
                            VALUES (%s, %s, %s, %s)
                            """, [product_name, BagName, quantity,0])

            transaction.commit_unless_managed()
            return redirect('pantry:bag_product_list',BagName=BagName)
    else:
        form = AddToBagForm(initial={'BagName':BagName}) # An unbound form
    return render(request, 'pantry/add_product_to_bag.html', {'form': form, 'BagName': BagName})

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
	if request.is_ajax():
		q = request.GET.get('q')
		if q is not None:     
			cursor = connection.cursor()
			cursor.execute("""
							SELECT CLName, CFName, Apt || " " || Street || " " || City || ", " || State || " " || Zip as Address, CPhone, Start
							FROM Client
							WHERE CLName LIKE %s OR CFName like %s OR CPhone like %s;
							""",['%' + q + '%', '%' + q + '%', '%' + q + '%'])
			clients = cursor.fetchall()
			return render_to_response('pantry/client_table.html',{ 'clients':clients },context_instance = RequestContext(request))

	cursor = connection.cursor()
	cursor.execute("""
					SELECT CLName, CFName, Apt || " " || Street || " " || City || ", " || State || " " || Zip as Address, CPhone, Start
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
				#client_reference_id = topCID[0] + 1
				#print client_reference_id
                #need this line after altering database in django 1.5
				transaction.commit_unless_managed()
			except IntegrityError:
				return render(request, 'pantry/add_client.html', {'form': form, 'error_message':'Client already exists'})
            #return redirect('pantry:product_list', kwargs={"success_message":smsg})
			return HttpResponseRedirect(reverse('pantry:add_family'))
	else:
		form = CreateClientForm() # An unbound form
	return render(request, 'pantry/add_client.html', {'form': form,})
	
def view_pickups(request):
    if request.is_ajax():
        q = request.GET.get('q')
        tt = request.GET.get('tt')
        cursor = connection.cursor()
        
        #view scheduled pickups
        if tt == "scheduled":        
            if q != "":
                    cursor.execute("""
                                    SELECT CLName, CFName, ifnull(Size,0)+1, Apt, Street, City, State, Zip, CPhone, PDay, Client.CID
                                    FROM Client 
                                    LEFT JOIN family_size 
                                    ON Client.CID = family_size.CID
                                    WHERE PDay = %s
                                   """,[q])
            else:
                cursor.execute("""
                                SELECT CLName, CFName, ifnull(Size,0)+1, Apt, Street, City, State, Zip, CPhone, PDay, Client.CID
                                FROM Client 
                                LEFT JOIN family_size 
                                ON Client.CID = family_size.CID
                               """)
       
            pickups = cursor.fetchall()
            return render_to_response('pantry/pickup_table.html',{ 'pickups':pickups })
            
        #view completed pickups
        else:
            if q != "":
                cursor.execute("""
                                SELECT CLName, CFName, BagName,PDay, Date
                                FROM PickupTransaction
                                JOIN Client
                                ON Client.CID = PickupTransaction.CID
                                WHERE PDay = %s
                               """,[q])
            else:
                cursor.execute("""
                                SELECT CLName, CFName, BagName, PDay, Date
                                FROM PickupTransaction
                                JOIN Client
                                ON Client.CID = PickupTransaction.CID
                               """)
            pickups = cursor.fetchall()
            return render_to_response('pantry/completed_pickup_table.html',{ 'pickups':pickups })
        

    cursor = connection.cursor()
    cursor.execute("""
                    CREATE VIEW if not exists family_size AS 
                    SELECT CID, COUNT(CID) AS Size
                    FROM FamilyMember
                    GROUP BY CID;
                   """)
    cursor.execute("""
                    SELECT CLName, CFName, ifnull(Size,0)+1, Apt, Street, City, State, Zip, CPhone, PDay, Client.CID
                    FROM Client 
                    LEFT JOIN family_size 
                    ON Client.CID = family_size.CID
                   """)
    pickups = cursor.fetchall()
    return render(request, 'pantry/pickup_list.html',{
        'pickups':pickups
    })
    
def complete_pickup(request,cid):

    cursor = connection.cursor()
    
    #user has clicked confirm pickup
    if request.method == 'POST':
    
        cursor.execute("""
                        INSERT INTO PickupTransaction
                        VALUES(null,%s,%s)
                        """,[cid,datetime.date.today()])
        transaction.commit_unless_managed()
        
        return HttpResponseRedirect(reverse('pantry:pickup_list'))
    
    
    cursor.execute("""
                    SELECT BagName
				    FROM Client
				    WHERE CID = %s
				    """,[cid])
    bag_name = cursor.fetchone()[0]
    
    cursor.execute("""
					SELECT ProductName, CurrentMnthQty as Quantity
					FROM Holds 
					WHERE BagName = %s
					""",[bag_name])
    bag = cursor.fetchall()
	
    cursor.execute("""
					SELECT CFName,CLName
					FROM Client
					WHERE CID = %s
					""",[cid])
					
    temp = cursor.fetchone()
    name = temp[0] + " " + temp[1]
    return render(request, 'pantry/complete_pickup.html',{
        'bag':bag,
        'name':name,
        'bag_name':bag_name,
        'date':datetime.date.today()
    })

def add_family_member(request):
	if request.method == 'POST': # If the form has been submitted...
		form = AddFamilyMemberForm(request.POST) # A form bound to the POST data
		if form.is_valid(): # All validation rules pass
			first_name = form.cleaned_data['first_name']
			last_name = form.cleaned_data['last_name']
			gender = form.cleaned_data['gender']
			DOB = form.cleaned_data['DOB']
			cursor = connection.cursor()
            
			try:
				cursor.execute("SELECT CID FROM Client ORDER BY CID desc")
				topCID = cursor.fetchone()				
				cursor.execute("INSERT INTO FamilyMember VALUES (%s,%s,%s,%s,%s)", 
				[topCID[0], first_name, last_name, DOB, gender])
				
                #need this line after altering database in django 1.5
				transaction.commit_unless_managed()
			except IntegrityError:
				return render(request, 'pantry/add_family.html', {'form': form, 'error_message':'Family member already exists'})
            #return redirect('pantry:product_list', kwargs={"success_message":smsg})
			return HttpResponseRedirect(reverse('pantry:add_family'))
	else:
		form = AddFamilyMemberForm() # An unbound form
	return render(request, 'pantry/add_family.html', {'form': form,})
	
def view_reports(request):
    cursor = connection.cursor()	
    cursor.execute("DROP VIEW if exists PickupClient")
    if request.is_ajax():
        rm = request.GET.get('rm')
        rt = request.GET.get('rt')
        if rt == "service":
            if rm == "active":
                cursor.execute("""
    							CREATE VIEW if not exists PickupClient AS
    							SELECT c.CID, CASE
    							  WHEN c.DOB > date('2013-11-25','-18 years') THEN 0
    							  WHEN c.DOB <= date('2013-11-25','-18 years') AND c.DOB >= date('2013-11-25','-65 years') THEN 1
    							  ELSE 2
    							  END AS agegroup,
    							  CASE
    							  WHEN PDay < 8 THEN 1
    							  WHEN PDay >= 8 AND PDay < 15 THEN 2
    							  WHEN PDay >= 15 AND PDay < 22 THEN 3
    							  WHEN PDay >= 22 AND PDay < 29 THEN 4
    							  ELSE 5
    							  END AS week,PDay,Cost1, PickupTransaction.date
    							FROM(
    							SELECT CID, DOB FROM familyMember
    							UNION ALL
    							SELECT CID, DOB FROM Client) as c
    							JOIN Client
    							JOIN bag_cost 
    							JOIN PickupTransaction
    							WHERE c.CID = Client.CID AND bag_cost.BagName = Client.BagName 
								AND c.CID = PickupTransaction.CID AND strftime('%m',Date) = strftime('%m',date('2013-11-25'))
    							ORDER BY Week;
    							""")
            elif rm == "last_month":
                cursor.execute("""
    							CREATE VIEW if not exists PickupClient AS
    							SELECT c.CID, CASE
    							  WHEN c.DOB > date('2013-11-25','-18 years') THEN 0
    							  WHEN c.DOB <= date('2013-11-25','-18 years') AND c.DOB >= date('2013-11-25','-65 years') THEN 1
    							  ELSE 2
    							  END AS agegroup,
    							  CASE
    							  WHEN PDay < 8 THEN 1
    							  WHEN PDay >= 8 AND PDay < 15 THEN 2
    							  WHEN PDay >= 15 AND PDay < 22 THEN 3
    							  WHEN PDay >= 22 AND PDay < 29 THEN 4
    							  ELSE 5
    							  END AS week,PDay,Cost1, PickupTransaction.date
    							FROM(
    							SELECT CID, DOB FROM familyMember
    							UNION ALL
    							SELECT CID, DOB FROM Client) as c
    							JOIN Client
    							JOIN bag_cost 
    							JOIN PickupTransaction
    							WHERE c.CID = Client.CID AND bag_cost.BagName = Client.BagName AND c.CID = PickupTransaction.CID 
								AND strftime('%m',Date) = strftime('%m',date('2013-11-25','-1 months'))
    							ORDER BY Week;
    				""")
                cursor.execute("""
    				CREATE VIEW if not exists almost as
    				SELECT fullweek.week, count(Distinct CID) as [num_households],
                        (CASE WHEN a.nums IS NULL THEN 0 ELSE a.nums END) AS [u18],
                        (CASE WHEN b.nums IS NULL THEN 0 ELSE b.nums END) AS [18-64],
                        (CASE WHEN c.nums IS NULL THEN 0 ELSE c.nums END) AS [65+],
                        count(CID) AS [Total People]
                    FROM (weeks
                    LEFT JOIN pickupclient on pickupclient.week = weeks.week) as fullweek
                    LEFT JOIN a on fullweek.week = a.week 
                    LEFT JOIN b on fullweek.week = b.week
                    LEFT JOIN c on fullweek.week = c.week
                    GROUP BY fullweek.week;
    				""")
    		cursor.execute("""
    						CREATE VIEW if not exists tot_food_cost AS
    						SELECT week, sum(cost1) as total_cost
    						FROM (SELECT DISTINCT CID, cost1, week FROM Pickupclient)
    						GROUP BY week;
    						""")
    		cursor.execute("""
    						SELECT almost.week, almost.num_households, almost.u18, almost.[18-64], almost.[65+], almost.[Total People], ifnull(tot_food_cost.[total_cost],0)
                            FROM almost LEFT JOIN tot_food_cost
                            ON almost.week = tot_food_cost.week;
    						""")
    		data = cursor.fetchall()
    		cursor.execute("""
    						SELECT sum(num_households),sum(u18),sum([18-64]),sum([65+]),
    						sum([total people]), sum(total_cost)
    						FROM almost NATURAL JOIN tot_food_cost;
    						""")
    		totals = cursor.fetchone()
    		cursor.execute("DROP VIEW PickupClient")
    		return render(request, 'pantry/service_report_table.html', {'data': data, 'totals':totals})
    	else: 
    	    cursor.execute("""
    	                    CREATE VIEW if not exists gl_now AS
                            SELECT Client.BagName, ProductName, CurrentMnthQty as CMQ
                            FROM Client
                            JOIN Holds 
                            WHERE Holds.BagName = Client.BagName;""")
            cursor.execute("""                
                            CREATE VIEW if not exists gl_past AS
                            SELECT Client.BagName, ProductName, LastMnthQty as LMQ,date 
                            FROM Pickuptransaction 
                            JOIN Client
                            JOIN Holds 
                            WHERE Pickuptransaction.CID = Client.CID AND Holds.BagName = Client.BagName
							AND  strftime('%m',date(date)) = strftime('%m',date('2013-11-25','-1 months'));""")

            cursor.execute("""                
                            CREATE VIEW if not exists groc_list AS
                            SELECT gl_now.ProductName AS prodname, CMQ, LMQ
                            FROM gl_now LEFT JOIN gl_past 
                            ON gl_now.ProductName=gl_past.ProductName;""")

                      

            cursor.execute("""
                            SELECT prodname AS Product, SUM(CMQ) as Quantity, SUM(ifnull(LMQ,0)) as [Last Month Quantity] 
                            FROM groc_list
                            GROUP BY prodname;""")
            products = cursor.fetchall()
            return render(request, 'pantry/grocery_list_table.html', {'products': products})            
    else:
		cursor.execute("""
						CREATE VIEW if not exists PickupClient AS
						SELECT c.CID, CASE
						  WHEN c.DOB > date('2013-11-25','-18 years') THEN 0
						  WHEN c.DOB <= date('2013-11-25','-18 years') AND c.DOB >= date('2013-11-25','-65 years') THEN 1
						  ELSE 2
						  END AS agegroup,
						  CASE
						  WHEN PDay < 8 THEN 1
						  WHEN PDay >= 8 AND PDay < 15 THEN 2
						  WHEN PDay >= 15 AND PDay < 22 THEN 3
						  WHEN PDay >= 22 AND PDay < 29 THEN 4
						  ELSE 5
						  END AS week,PDay,Cost1, PickupTransaction.date
						FROM(
						SELECT CID, DOB FROM familyMember
						UNION ALL
						SELECT CID, DOB FROM Client) as c
						JOIN Client
						JOIN bag_cost 
						JOIN PickupTransaction
						WHERE c.CID = Client.CID AND bag_cost.BagName = Client.BagName AND c.CID = PickupTransaction.CID 
						AND strftime('%m',Date) = strftime('%m',date('2013-11-25'))
						ORDER BY Week;
						""")
		cursor.execute("""
						CREATE VIEW if not exists almost as
						SELECT pickupclient.week, count(Distinct CID) as [num_households],
							(CASE WHEN a.nums IS NULL THEN 0 ELSE a.nums END) AS [u18],
							(CASE WHEN b.nums IS NULL THEN 0 ELSE b.nums END) AS [18-64],
							(CASE WHEN c.nums IS NULL THEN 0 ELSE c.nums END) AS [65+],
							count(CID) AS [Total People]
						FROM Pickupclient
						LEFT JOIN a on pickupclient.week = a.week 
						LEFT JOIN b on pickupclient.week = b.week
						LEFT JOIN c on pickupclient.week = c.week
						GROUP BY pickupclient.week
						""")
		cursor.execute("""
						CREATE VIEW if not exists tot_food_cost AS
						SELECT week, sum(cost1) as total_cost
						FROM (SELECT DISTINCT CID, cost1, week FROM Pickupclient)
						GROUP BY week;
						""")
		cursor.execute("""
						SELECT *
						FROM almost NATURAL JOIN tot_food_cost
						""")
		data = cursor.fetchall()
		cursor.execute("""
						SELECT sum(num_households),sum(u18),sum([18-64]),sum([65+]),
						sum([total people]), sum(total_cost)
						FROM almost NATURAL JOIN tot_food_cost;
						""")
		totals = cursor.fetchone()
		return render(request, 'pantry/reports.html', {'data': data, 'totals':totals})
    

    
