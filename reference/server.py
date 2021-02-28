
from flask import Flask, render_template, request, g, redirect, url_for, jsonify, abort, session, send_file
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
import os, math

import db, io
from auth0 import auth0_setup, require_auth, auth0



app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

# have the DB submodule set itself up before we get started. groovy.
@app.before_first_request
def initialize():
    db.setup()
    auth0_setup()


### AUTH:
@app.route('/login')
def login():
    if 'profile' in session:
        return redirect(url_for('test_auth'))
    else:
        return auth0().authorize_redirect(redirect_uri=url_for('callback', _external=True))

@app.route('/logout')
def logout():
    session.clear()
    params = { 'returnTo': url_for('home', _external=True), 'client_id': os.environ['AUTH0_CLIENT_ID'] }
    return redirect(auth0().api_base_url + '/v2/logout?' + urlencode(params))

@app.route('/callback')
def callback():
    auth0().authorize_access_token()
    resp = auth0().get('userinfo')
    userinfo = resp.json()

    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }

    return redirect('/test_auth')

@app.route('/test_auth')
@require_auth
def test_auth():
    return render_template("test_auth.html", profile=session['profile'])



### IMAGES
@app.route('/image/<int:img_id>')
def view_image(img_id):
    with db.get_db_cursor() as cur:
        cur.execute("SELECT * FROM images where image_id=%s", (img_id,))
        image_row = cur.fetchone() # just another way to interact with cursors

        # in memory pyhton IO stream
        stream = io.BytesIO(image_row["data"])

        # use special "send_file" function
        return send_file(stream, attachment_filename=image_row["filename"])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['png', 'jpg', "gif"]


@app.route('/image', methods=['POST'])
@require_auth
def upload_image():
    # check if the post request has the file part
    if 'image' not in request.files:
        return redirect(url_for("image_gallery", status="Image Upload Failed: No selected file"))
    file = request.files['image']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return redirect(url_for("image_gallery", status="Image Upload Failed: No selected file"))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        data = file.read()
        with db.get_db_cursor(True) as cur:
            cur.execute("insert into images (filename, data) values (%s, %s)", (filename, data))
    return redirect(url_for("image_gallery", status="Image Uploaded Succesfully"))

def try_parse_int(s, base=10, default=None):
    """Parse an integer with a default"""
    try:
        return int(s, base)
    except ValueError:
        return default


@app.route('/image', methods=['GET'])
def image_gallery():
    status = request.args.get("status", "")
    page = try_parse_int(request.args.get("page", "0"), default=0)
    IMAGES_PER_PAGE = 6

    with db.get_db_cursor() as cur:
        cur.execute("select image_id from images order by image_id desc limit %s offset %s ;", (IMAGES_PER_PAGE, page*IMAGES_PER_PAGE))
        imageIds = [r[0] for r in cur]
        cur.execute("select count(*) from images;")
        image_count = cur.fetchone()[0]
        max_page = math.ceil(1.0 * image_count / IMAGES_PER_PAGE) - 1
        return render_template("gallery.html", imageIds = imageIds, status=status, page=page, max_page=max_page)




### ROOT
@app.route('/')
def home():
    user_name = request.args.get("userName", "unknown")
    return render_template('main.html', user=user_name)


@app.errorhandler(404)
def error404(error):
    return "oh no. you killed it."


@app.route('/api/foo')
def api_foo():
    data = {
        "message": "hello, world",
        "isAGoodExample": False,
        "aList": [1, 2, 3],
        "nested": {
            "key": "value"
        }
    }
    return jsonify(data)


### PEOPLE
@app.route('/people', methods=['GET'])
def people():
    with db.get_db_cursor() as cur:
        cur.execute("SELECT name FROM person;")
        names = [record[0] for record in cur]

        return render_template('people.html', names=names)

@app.route('/people', methods=['POST'])
def new_person():
    with db.get_db_cursor(True) as cur:
        name = request.form.get("name", "unnamed friend")
        app.logger.info("Adding person %s", name)
        cur.execute("INSERT INTO person (name) values (%s)", (name,))

        return redirect(url_for('people'))


@app.route('/people/<int:id>', methods=['GET'])
def get_person(id):
    with db.get_db_cursor(False) as cur:
        cur.execute("SELECT name, description from person where person_id = %s;", (id,))
        people = [record for record in cur];
        if(len(people) == 0):
            return abort(404)
        else:
            return render_template("person.html", name=people[0][0], desc=people[0][1], id=id)

@app.route('/people/<int:id>', methods=['POST'])
def edit_person(id):
    description = request.form.get("description")
    with db.get_db_cursor(True) as cur:
        cur.execute("UPDATE person set description = %s where person_id = %s;", (description, id))
        return redirect(url_for("get_person", id=id))
