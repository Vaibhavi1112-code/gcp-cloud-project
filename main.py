import os, io
import google.generativeai as genai
from flask import Flask, request, redirect, render_template_string, send_file, session, flash, get_flashed_messages, make_response
from google.cloud import storage
import datetime
import requests
import json
from google.cloud import firestore
import pyrebase
from urllib3.contrib import appengine
import six.moves
import traceback
from datetime import datetime, timedelta
import pytz 

storage_client = storage.Client()
bucket_name = 'vaibhavipanchal-project1'
bucket = storage_client.bucket(bucket_name)
bucket.blob('files/photosaver-435516-e3a398728fa3.json').download_to_filename('photosaver-435516-e3a398728fa3.json')
firebase_apikey = bucket.blob('files/firebase_apikey.txt').download_as_text()
gemini_apikey = bucket.blob('files/gemini_apikey.txt').download_as_text()

# Firebase configuration
firebaseConfig = {
    "apiKey": f"{firebase_apikey}",
    "authDomain": "photosaver-435516.firebaseapp.com",
    "projectId": "photosaver-435516",
    "storageBucket": "photosaver-435516.appspot.com",
    "databaseURL": "https://photosaver-435516.firebaseio.com",
    "serviceAccount": "photosaver-435516-e3a398728fa3.json"
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

app = Flask(__name__)
app.secret_key = bucket.blob('files/app_secret_key.txt').download_as_text()
db = firestore.Client(database='photosaver')
SESSION_EXPIRATION_MINUTES = 5
EASTERN_TIMEZONE = pytz.timezone("America/New_York")

genai.configure(api_key=f"{gemini_apikey}")
#genai.configure(api_key=os.environ["GEMINI_API_KEY"])

# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)

def upload_to_gemini(file, mime_type=None):
    file.seek(0)
    response = genai.upload_file(io.BytesIO(file.read()), mime_type=file.content_type)
    print("file uploaded to Gemini")
    return response

def upload_to_bucket(source_file, filename):
    blob = bucket.blob(filename)
    blob.upload_from_file(source_file)
    return blob.public_url


def download_file(filename):
    blob = bucket.blob(filename)
    if blob.exists():
        image_bytes = blob.download_as_bytes()
        image_stream = io.BytesIO(image_bytes)
        image_stream.seek(0)

        file_extension = os.path.splitext(filename)[1].lower()

        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.txt': 'text/plain'
        }
        mime_type = mime_types.get(file_extension, 'application/octet-stream')

        return send_file(
            image_stream,
            as_attachment=False,
            download_name=filename,
            mimetype=mime_type
        )
    return 'File not found.', 404


@app.route('/')
def index():
    if auth.current_user:
        user_id = session.get('usr')
        db.collection('sessions').document(user_id).update({
            'logged_in': True
        })
    user_id = session.get('usr')
    if True:    
        if user_id:
            user_session = db.collection('sessions').document(user_id).get()
            if user_session.exists:
                session_data = user_session.to_dict()
                login_status = session_data.get('logged_in', False)
                if login_status:
                    last_active = session_data.get('last_active')
                    expiration_time = last_active + timedelta(minutes=SESSION_EXPIRATION_MINUTES)
                    current_time = datetime.now(EASTERN_TIMEZONE)
                    if current_time > expiration_time:
                        db.collection('sessions').document(user_id).update({
                            'logged_in': False
                        })
                        session.pop('user_id', None)
                        return redirect('/login.html')
                    db.collection('sessions').document(user_id).update({
                        'last_active': datetime.now(EASTERN_TIMEZONE)
                    })
                    current_user = session['email'].split('@')[0]
                    blobs = bucket.list_blobs(prefix=current_user + '/')
                    files = [(blob.name, blob.name.split('/')[-1]) for blob in blobs if blob.name.endswith(('.jpeg', '.jpg', '.png', '.txt'))]
                    index_html = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Upload and View Images</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            color: #333;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        header {
            background-color: #007bff;
            color: white;
            width: 100%;
            padding: 10px 0;
            text-align: center;
            position: fixed;
            top: 0;
            left: 0;
            z-index: 1000;
        }
        main {
            padding-top: 60px; /* Space for fixed header */
            width: 90%;
            max-width: 800px;
            margin: 20px auto;
        }
        h1 {
            color: #007bff;
        }
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
        }
        form {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        form div {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="file"] {
            display: block;
            width: 100%;
            margin: 0;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #fff;
        }
        button {
            background-color: #dc3545; /* Red for submit button */
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            border-radius: 4px;
        }
        button:hover {
            background-color: #c82333; /* Darker red on hover */
        }
        .logout-button {
            background-color: #dc3545; /* Red for logout button */
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            border-radius: 4px;
            margin-left: 10px; /* Add spacing between the buttons */
        }
        ul {
            list-style: none;
            padding: 0;
        }
        li {
            display: inline-block;
            margin: 10px;
        }
        img {
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        @media (max-width: 768px) {
            img {
                width: 100%;
                height: auto;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>Image Upload and Viewer</h1>
    </header>
    <main>
        <div class="header-container">
            <h2>Upload Image</h2>
            <a href="/logout" style="text-decoration: none;">
                <button class="logout-button">Logout</button>
            </a>
        </div>
        <body style="background-color: rgb(51, 204, 254);">
        <form method="post" enctype="multipart/form-data" action="/upload">
            <div>
                <label for="file">Choose file to upload</label>
                <input type="file" id="file" name="form_file" accept="image/jpeg, image/jpg, image/png"/>
            </div>
            <div>
                <button type="submit">Submit</button>
            </div>
        </form>
        <h2>Uploaded Images</h2>
        <ul>
                
        </ul>
    </main>
</body>
</html>

'''

                    for full_path, filename in files:
                        index_html += f'<li><a href="/files/{full_path}">{filename}</a></li>'
                    index_html += '</ul>'
                    response = make_response(index_html)  # Create a response with the HTML content
                    response.headers['Cache-Control'] = 'no-store'  # Disable caching
                    response.headers['Pragma'] = 'no-cache'  # Disable caching
                    response.headers['Expires'] = '0'  # Disable caching

                    return response  # Return the response
                else:
                    return redirect('/login.html')
            else:
                return redirect('/login.html')
        else:
            return redirect('/login.html')
    else:
        return redirect('/login.html')
  
@app.route('/login.html')
def login_html():
    messages = get_flashed_messages()
    message_html = "<h3>" + "</h3><h3>".join(messages) + "</h3>" if messages else ""
    login_html = f"""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Login to Photo App</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            color: #333;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        header {{
            background-color: #007bff;
            color: white;
            width: 100%;
            padding: 10px 0;
            text-align: center;
            position: fixed;
            top: 0;
            left: 0;
            z-index: 1000;
        }}
        main {{
            padding-top: 60px; /* Space for fixed header */
            width: 90%;
            max-width: 400px;
            margin: 20px auto;
        }}
        h1 {{
            color: #007bff;
        }}
        form {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        form div {{
            margin-bottom: 15px;
        }}
        label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }}
        input[type="text"],
        input[type="password"] {{
            display: block;
            width: 100%;
            margin: 0;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #fff;
        }}
        button {{
            background-color: #dc3545; /* Red color */
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            border-radius: 4px;
            width: 100%; /* Full width button */
        }}
        button:hover {{
            background-color: #c82333; /* Darker red on hover */
        }}
    </style>
</head>
<body>
    <header>
        <h1>Login to Photo App</h1>
    </header>
    <main> 
        <body style="background-color: rgb(51, 204, 254);">
        <h2>Please login to the Photo App</h2><br>
        <form method="post" action="/login">
            <div>
                <label for="user">Email</label><br>
                <input type="text" id="user" name="user" required>
            </div>
            <div>
                <label for="pwd">Password</label><br>
                <input type="password" id="pwd" name="pwd" required>
            </div>
            <div>
                <button type="submit">Login</button>
            </div>
        </form>
        {message_html}
    </main>
</body>
</html>
    """
    return render_template_string(login_html)

@app.route('/login', methods=["POST"])
def login():
    print("POST /login")
    email = request.form['user']
    password = request.form['pwd']
    message = ""
    
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        user = auth.refresh(user['refreshToken'])
        user_id = user['idToken']
        session['usr'] = user_id
        session['email'] = email

        db.collection('sessions').document(user_id).set({
            'logged_in': True,
            'last_active': datetime.now(EASTERN_TIMEZONE)
        })

        return redirect('/')
    except Exception as e:
        print(f"Error during login: {str(e)}")
        flash("Login Error: Incorrect Email or Password!")
        return redirect('/login.html')

@app.route('/logout')
def logout():
    user_id = session.pop('usr', None)
    if user_id:
         db.collection('sessions').document(user_id).update({
            'logged_in': False
        })
    response = redirect('/login.html') 
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Pragma'] = 'no-cache'  
    return response

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['form_file']
    
    if file and file.filename.endswith(('.jpeg', '.jpg', '.png')):
        user = session.get('email').split('@')[0]
        user = str(user) + "/"
        print("USER : " + user)
        public_url_img = upload_to_bucket(file, user + file.filename)
        gemini_response = [upload_to_gemini(file)]
        print(gemini_response)

        chat_session = model.start_chat()
        chat_session.send_message("Hello!")
        chat_session.send_message(gemini_response[0])
        response = chat_session.send_message("Give a caption and a short description of uploaded image in JSON format")
        print(response.text)

        text_filename = file.filename.split('.')[0] + '.txt'
        print(text_filename)

        with io.BytesIO(response.text.encode('utf-8')) as text_file:
            text_file.seek(0)
            upload_to_bucket(text_file, user + text_filename)

        return redirect('/')
    return 'Invalid file type or no file uploaded.', 400



@app.route('/files/<path:filename>')
def get_file(filename):
    print("GET FILE NAME : " + filename)
    return download_file(filename=filename)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
