from flask import Flask, jsonify, render_template, request, send_from_directory
import firebase_admin
from firebase_admin import credentials, db
import base64
from PIL import Image
import tabulate
from functions import *
import io
import google.generativeai as genai

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

genai.configure(api_key=os.getenv('api_key'))


model = genai.GenerativeModel("gemini-1.5-flash")
cred = credentials.Certificate('Credentials.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://crave-check-3c368-default-rtdb.asia-southeast1.firebasedatabase.app/'  
})
print("Firebase initialized successfully") 

name=None
username=None
username_available=[]
userdata={}

app = Flask(__name__, template_folder='templates')
app.secret_key = 'your_secret_key'

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/')
def index():
    global username_available
    ref = db.reference('/users')
    users_data = ref.get()
    username_available = list(users_data.keys()) if users_data else []
    print(username_available)
    return render_template('index.html')

@app.route('/Home', methods=['POST','GET'])
def home():
    global name,username,username_available
    ref = db.reference('/users')
    users_data = ref.get()
    username_available = list(users_data.keys()) if users_data else []
    if name!=None:
        return render_template('index.html',name=name,username=username)
    return render_template('index.html')

@app.route('/signed_in', methods=['GET', 'POST'])
def signed_in():
    global name, username, username_available
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        print(f"Received form data - Name: {name}, Username: {username}")
        if not name or not username:
            print("No form data received, opening camera for direct entry")
            return render_template('scan_image.html', name='', username='')
        username=username.lower()
        password = request.form.get('password')
        age = request.form.get('age')
        if age is None or age.strip() == '':
            message = "Age is required. Please provide your age."
            return render_template('signup.html', error_message=message, username_available=username_available)
        try:
            age = int(age)  
        except ValueError:
            message = "Invalid age value. Please enter a valid number."
            return render_template('signup.html', error_message=message, username_available=username_available)
        gender = request.form.get('gender')
        ref = db.reference(f'/users/{username}')
        user_data = ref.get()
        if user_data:
            message = f"Username '{username}' is already taken. Please choose a different one."
            return render_template('signup.html', error_message=message, username_available=username_available)
        allergies_list = {
            'Allergies': {
                'Gluten': 1 if 'Gluten' in request.form.getlist('allergies') else 0,
                'Peanuts': 1 if 'Peanuts' in request.form.getlist('allergies') else 0,
                'Tree Nuts': 1 if 'Tree Nuts' in request.form.getlist('allergies') else 0,
                'Dairy': 1 if 'Dairy' in request.form.getlist('allergies') else 0,
                'Eggs': 1 if 'Eggs' in request.form.getlist('allergies') else 0,
                'Shellfish': 1 if 'Shellfish' in request.form.getlist('allergies') else 0,
                'Fish': 1 if 'Fish' in request.form.getlist('allergies') else 0,
                'Soy': 1 if 'Soy' in request.form.getlist('allergies') else 0,
                'Wheat': 1 if 'Wheat' in request.form.getlist('allergies') else 0,
                'Sesame': 1 if 'Sesame' in request.form.getlist('allergies') else 0
            }
        }
        dietary = request.form.get('dietary')
        health_conditions_list = {
            'Health Conditions': {
                'Diabetes': 1 if 'Diabetes' in request.form.getlist('health_conditions') else 0,
                'High Cholesterol': 1 if 'High Cholesterol' in request.form.getlist('health_conditions') else 0,
                'Heart Conditions': 1 if 'Heart Conditions' in request.form.getlist('health_conditions') else 0,
                'Obesity': 1 if 'Obesity' in request.form.getlist('health_conditions') else 0,
                'Kidney Disease': 1 if 'Kidney Disease' in request.form.getlist('health_conditions') else 0,
                'Hypertension': 1 if 'Hypertension' in request.form.getlist('health_conditions') else 0
            }
        }
        religious_restrictions = {
            'Jain': 1 if request.form.get('religious_restrictions') == 'Jain' else 0
        }
        food_preferences = {
            'Organic': 1 if request.form.get('food_preferences') == 'Organic' else 0
        }
        try:
            ref.set({
                'Name': name,
                'Age': age,
                'Password': password,
                'Gender': 'M' if gender == 'Male' else 'F',
                **allergies_list,
                'Dietary': dietary,
                **health_conditions_list,
                **religious_restrictions,
                **food_preferences
            })
            print(f"User '{username}' created successfully in Firebase!")
        except Exception as e:
            print(f"Error saving data to Firebase: {e}")
            message = "There was an issue saving your data. Please try again."
            return render_template('signup.html', error_message=message, username_available=username_available)
        ref = db.reference('/users')
        users_data = ref.get()
        username_available = list(users_data.keys()) if users_data else []
        print(username_available)
        return render_template('index.html', name=name, username=username)
    return render_template('index.html', name=name, username=username)

@app.route('/check_username', methods=['POST'])
def check_username():
    username = request.form.get('username')
    ref = db.reference(f'/users/{username}')
    user_data = ref.get()
    if user_data:
        return jsonify({'exists': True})  
    else:
        return jsonify({'exists': False})

@app.route('/signup', methods=['POST'])
def signup():
    global username_available
    print('In sign up') 
    return render_template('signup.html', username_available=username_available)

@app.route('/login', methods=['GET', 'POST'])
def login():
    global username_available,username,name
    if request.method == 'POST':
        username1 = request.form.get('username')
        password = request.form.get('password')
        if username1 is None:
            return render_template('login.html')
        if username1.lower() not in username_available:
            message = f"Username '{username1}' does not exist."
            return render_template('login.html', error_message=message)
        ref = db.reference(f'/users/{username1.lower()}')
        user_data = ref.get()
        if user_data and user_data['Password'] == password:
            print(f"User '{username1}' logged in successfully!")
            name=user_data['Name']
            username=username1.lower()
            return render_template('index.html', name=user_data['Name'], username=username1.lower())
        else:
            message = "Incorrect password. Please try again."
            return render_template('login.html', error_message=message)
    return render_template('login.html')

@app.route('/Image_process', methods=['POST','GET'])
def image_process():
    global name,username
    return render_template('scan_image.html',name=name,username=username)

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    global username, name
    user_data = None
    product_name, product_data, consume_safe= '', '', ''
    product_report=[]
    if request.method == 'POST':
        if username is not None:
            ref = db.reference(f'/users/{username.lower()}')
            user_data = ref.get()
        image_data = request.form.get('image')
        if image_data:
            try:
                header, encoded = image_data.split(',', 1)
                file_extension = header.split(';')[0].split('/')[1]
                file_extension = 'jpeg' if file_extension == 'jpg' else file_extension
                image = Image.open(io.BytesIO(base64.b64decode(encoded)))
                image.save(f"static/captured_image/product_image.{file_extension}", format=file_extension.upper())
                image_address=f"static/captured_image/product_image.{file_extension}"
                product_name, product_data = product_details(image_address, name, username)
                consume_safe, personal_detail = check_product_safety(product_data,user_data)
                result = analyze_product_and_environmental_impact_from_image(image_address)

                if isinstance(result, str):
                    print(f"Error{result}")
                    return render_template('scan_image.html', name=name, username=username, error_message=f'Error processing the image. Retake the image'), 500

                else:
                    consumable, ingredients, nutrition_table, details, alternatives = result
                    if consumable == "NO":
                        consume_safe = "NO"
                        personal_detail = 'NOT FOR CONSUMPTION'
                    table_message = tabulate(nutrition_table, headers=nutrition_table.columns, tablefmt="html", numalign="center", stralign="center", showindex=False)
                    message = table_message.replace('<table>', '<table class="chat-table">')

                    if nutrition_table.empty:
                        product_report = [
                        '<span class="personal-detail">'+ personal_detail + '</span>',  
                        '<span class="ingredients-title">Ingredients: </span><br>' + ', '.join(ingredients), 
                        '<span class="health-effects-title">Health Effects: </span><br>' + '\n * '.join(details),  
                        '<span class="alternatives-title">Alternatives: </span><br>' + ', '.join(alternatives) 
                        ]
                    else:
                        product_report = [
                        '<span class="personal-detail">' + personal_detail + '</span>',  
                        '<span class="ingredients-title">Ingredients: </span><br>' + ', '.join(ingredients), 
                        '<span class="nutrition-title">Nutrition Value: </span><br>' + message,  
                        '<span class="health-effects-title">Health Effects: </span><br>' + '\n * '.join(details),  
                        '<span class="alternatives-title">Alternatives: </span><br>' + ', '.join(alternatives) 
                        ]


                return render_template('analyze.html', 
                                       name=name,
                                       product_name=product_name, 
                                       consume_safe=consume_safe, 
                                       product_report=product_report)

            except Exception as e:
                print(f"Line 220 {e}")
                return render_template('scan_image.html', name=name, username=username, error_message=f'Error processing the image. Retake the image'), 500
        
        return render_template('scan_image.html', name=name, username=username, error_message='No image data provided.'), 400

    return render_template('scan_image.html', name=name, username=username)
 
if __name__ == '__main__':
    app.run(debug=True)
