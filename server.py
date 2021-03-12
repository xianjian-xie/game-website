from flask import Flask, render_template, request, g, redirect, url_for, jsonify, abort, session, send_file
from werkzeug.utils import secure_filename
from urllib.parse import urlencode
from trie import Trie
import os, math

import db, io
from auth0 import auth0_setup, require_auth, auth0

import time
import datetime



app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

# have the DB submodule set itself up before we get started. groovy.
@app.before_first_request
def initialize():
    db.setup()
    auth0_setup()

@app.errorhandler(404)
def error404(error):
    return "oh no. you killed it."

### AUTH:
@app.route('/login')
def login():
    app.logger.info("The url is  %s",request.referrer)
    if 'profile' in session:
        return redirect(request.referrer)
        #return redirect(url_for('test_auth'))
    else:
        session['return_url'] = request.referrer
        return auth0().authorize_redirect(redirect_uri=url_for('callback', _external=True))

@app.route('/logout')
def logout():
    session.clear()
    #session['return_url'] = request.referrer
    params = { 'returnTo': request.referrer, 'client_id': os.environ['AUTH0_CLIENT_ID'] }
    # params = { 'returnTo': url_for('home', _external=True), 'client_id': os.environ['AUTH0_CLIENT_ID'] }
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

    with db.get_db_cursor(True) as cur:
        cur.execute("SELECT * from reviewer where oauth_id = %s;",(userinfo['sub'],))
        reviewers = [record for record in cur]
        #if login not in our database, put in
        if (len(reviewers) == 0):
            app.logger.info("Insert in user %s",userinfo['name'])
            cur.execute("INSERT INTO reviewer (oauth_id,name,avatarlink) values (%s,%s,%s)",(userinfo['sub'],userinfo['name'],userinfo['picture'],))

    app.logger.info("The url is  %s",session['return_url'])
    return redirect(session['return_url'])


###put render main and review page function here:
@app.route('/', methods=['GET'])
def home():
    if 'profile' in session:
        signin = True
    else:
        signin = False

    with db.get_db_cursor() as cur:
        #get all possible ratings
        cur.execute("SELECT * from game order by rating DESC limit 10")
        rating_game_list = [record for record in cur]
        app.logger.info("Inside list is %s %s %s %s %s %s %s %s %s %s",rating_game_list[0][0],rating_game_list[0][1],rating_game_list[0][2],rating_game_list[0][3],rating_game_list[0][4],rating_game_list[0][5],rating_game_list[0][6],rating_game_list[0][7],rating_game_list[0][8],rating_game_list[0][9])
        cur.execute("SELECT * from game order by popularity DESC limit 10")
        popularity_game_list = [record for record in cur]

        #select the most recent k reviews
        k=10
        #cur.execute("SELECT * from review order by timestamp DESC limit %s",(k,))
        cur.execute("SELECT * from review, reviewer where review.reviewer_id=reviewer.id order by timestamp DESC limit %s",(k,))
        reviews = [record for record in cur]

    return render_template('main.html',reviews=reviews,rating_game_list=rating_game_list,popularity_game_list=popularity_game_list,signin = signin)
        # redirect(url_for('home_trie_search',game_list=game_list,reviews=reviews, trie = trie))


@app.route('/<int:id>', methods=['GET'])
def game(id):

    with db.get_db_cursor(True) as cur:

        #first find if game exits in our database and extract game data
        cur.execute("SELECT  * from game where id = %s", (id,))
        #app.logger.info("game name %s",name)
        game = [record for record in cur][0]
        #app.logger.info("picture is %s",game[0][0])
        if(len(game) == 0):
            return abort(404)
        else:
            #modify popularity +1
            cur_popularity = game[3]
            cur_popularity = cur_popularity + 1
            cur.execute("UPDATE game set popularity = %s where id = %s",(cur_popularity,id,))

            #select pictures
            cur.execute("SELECT picture_id from game_picture where game_id = %s",(id,))
            pictures_id=[record[0] for record in cur]
            pictures= []
            for picture_id in pictures_id:
                cur.execute("SELECT picturelink from picture where id = %s",(picture_id,))
                picture = [record[0] for record in cur][0]
                pictures.append(picture)

            #select game tag
            cur.execute("SELECT * from game_tag where game_id = %s",(id,))
            tags = [record for record in cur]

            #may need to consider here is there is no tag

            #select the most recent k reviews for the game
            k=10
            cur.execute("SELECT * from review, reviewer where game_id = %s and review.reviewer_id=reviewer.id order by timestamp DESC",(id,))
            reviews = [record for record in cur]


            if (len(reviews) > k):
                reviews = reviews[:k]

            #tag is a nested list with count in tag[][1],reviews is a nest list with k reviews
            return render_template("game.html", game=game,tags=tags,reviews=reviews, pictures=pictures)

            #return render_template("game.html", name=name, picture=game[0][0], video_link= game[0][1],overall_rating=game[0][2],desciption=game[0][3],platform=game[0][4], \
            #tag=tag,reviewer=review[0],title=review[1],content=review[2],review_rating=review[3])


###put search, sort and submit review function here:

#search: input:game name, output:game page
#fuzzy search and auto-complete not implemented, may need further implementation (might have question here)
@app.route('/search', methods=['GET'])
def search():
    with db.get_db_cursor() as cur:

        name = request.args.get("global")
        app.logger.info("Search for game %s", name)
        #first find if game exits in our database and extract game data
        cur.execute("SELECT * from game where name like %s", ("%"+name+"%",))
        games = [record for record in cur]
        if(len(games) == 0):
            return abort(404)
        else:
            return render_template("search.html", games=games)


@app.route("/autocomplete", methods=['GET'])
def search_autocomplete():
    query = request.args.get("query")
    with db.get_db_cursor() as cur:
        cur.execute("SELECT name FROM game WHERE name like %s;", ("%"+query+"%", ))
        results = [x[0] for x in cur]
        return jsonify(results)



@app.route('/<int:id>', methods=['POST'])
def edit_person(id):
    description = request.form.get("description")
    rating = request.form.get("rating")
    ts=time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    with db.get_db_cursor(True) as cur:
        cur.execute("INSERT INTO review (reviewer_id, game_id, timestamp, title, content, rating) VALUES ('18', %s, %s, 'hello', %s, %s);", (id, timestamp, description,rating))
        return redirect(url_for("game", id=id))


#new review:input-review, return to game page
@app.route('/<int:id>',methods=['POST'])
def new_review(id):
    with db.get_db_cursor() as cur:

        #insert review into review table
        reviewer = requst.form.get("reviewer")#this might need to be changed by auth0 function
        title = request.form.get("title")
        content = request.form.get("content")
        rating = request.form.get("rating")

        app.logger.info("Insert review in database %s %s %s %s %s", reviewer,name,title,content,rating)
        cur.execute("INSERT INTO review (reviewer,game,title,content,rating) values (%s,%s,%s,%s,%s)", (reviewer,name,title,content,rating,))#if I do not put time, if would default put a timestamp

        #update game_tag table, this might need to be changed, assume what form give is a string list
        tags = request.form.get("tag")
        if tags != None:
            cur.execute("SELECT tag, count from game_tag where game = %s",(name,))
            exist_tag = [record[0] for record in cur]
            tag_count = [record[1] for record in cur]
            for tag in tags:
                if tag in exist_tag:
                    tag_index = exist_tag.index(tag)
                    new_count = tag_count[tag_index] + 1
                    cur.excute("UPDATE game_tag set count = %s where game = %s and tag = %s",(new_count,name,tag,))
                else:
                    new_count = 1
                    cur.excute("INSERT INTO game_tag (game,tag,count) values (%s,%s,%s)",(name,tag,new_count,))

        #may need to update tag table, this need furthur discussion

        #update overall rating in game table
        if rating != None:
            cur.execute("SELECT rating, review_number from game where name = %s",(name,))
            overall_rating = [record[0] for record in cur]#[0]
            review_number = [record[1] for record in cur]#[0]
            overall_rating = (overall_rating*review_number + rating)/(review_number+1)
            cur.excute("UPDATE game set rating = %s, review_number = %s where name = %s",(overall_rating,review_number+1,name,))

    return redirect(url_for('game',id=id))
