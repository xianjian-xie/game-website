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

###put render main and review page function here:
@app.route('/', methods=['GET'])
def home():
    
    with db.get_db_cursor() as cur:
        #may need a  game_list, set default as rating
        cur.execute("SELECT name from game order by rating DESC")
        game_list = [record[0] for record in cur]
        if (len(game_list) > 10):
            game_list = game_list[:10]


        #select the most recent k reviews
        k=5
        cur.execute("SELECT reviewer,timestamp,game,title,content,rating from review order by timestamp DESC")
        reviews = [record for record in cur]
        if (len(reviews) > k):
            reviews = reviews[:k]

        trie = Trie()
        cur.execute("SELECT name from game order by popularity DESC")
        trie_game_list = [record[0] for record in cur]
        for i in trie_game_list:
            trie.insert(i)

        redirect(url_for('home_trie_search',game_list=game_list,reviews=reviews, trie = trie))
 

# @app.route('/trie', methods=['GET'])
# def home_trie_search(game_list,reviews,trie):

#     #接到请求的处理，需要改
#     keyword = request.args.get("key")
#     trie = request.args.get("trie")
#     if keyword is not None and keyword != "":
#         returnlist = trie.getData()

#     return render_template('main.html', game_list=game_list,reviews=reviews, trie_list = returnlist)


@app.route('/<string:name>', methods=['POST'])
def edit_person(name):
    description = request.form.get("description")
    ts=time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    with db.get_db_cursor(True) as cur:
        cur.execute("INSERT INTO review (reviewer, game, timestamp, title, content, rating) VALUES ('3', %s, %s, 'hello', %s,'5');;", (name, timestamp, description))
        return redirect(url_for("game", name=name))

@app.route('/<string:name>', methods=['GET'])
def game(name):
    
    with db.get_db_cursor() as cur:

        #first find if game exits in our database and extract game data
        cur.execute("SELECT picture_link, video, rating, description, platform from game where name = %s;", (name,))
        #app.logger.info("game name %s",name)
        game = [record for record in cur]
        #app.logger.info("picture is %s",game[0][0])
        if(len(game) == 0):
            return abort(404)
        else:
            #select game tag
            cur.execute("SELECT tag, count from game_tag where game = %s",(name,))
            tag = [record for record in cur]

            #may need to consider here is there is no tag

            #select the most recent k reviews for the game
            k=10
            cur.execute("SELECT reviewer,timestamp,title,content,rating,oauth_id from review, reviewer where game = %s and review.reviewer=reviewer.id order by timestamp DESC",(name,))
            reviews = [record for record in cur]

            
            if (len(reviews) > k):
                reviews = reviews[:k]

            #tag is a nested list with count in tag[][1],reviews is a nest list with k reviews
            return render_template("game.html", name=name, picture=game[0][0], video_link= game[0][1],overall_rating=game[0][2],description=game[0][3],platform=game[0][4], tag=tag,reviews=reviews)

            #return render_template("game.html", name=name, picture=game[0][0], video_link= game[0][1],overall_rating=game[0][2],desciption=game[0][3],platform=game[0][4], \
            #tag=tag,reviewer=review[0],title=review[1],content=review[2],review_rating=review[3])

@app.route('/search/<string:name>', methods=['GET'])
def list_game(name):
    with db.get_db_cursor() as cur:

        #first find if game exits in our database and extract game data
        app.logger.info("game name %s",name)
        cur.execute("SELECT picture_link, video, rating, description, platform from game where name = %s;", (name,))
        game = [record for record in cur]
        #app.logger.info("picture is %s",game[0][0])
        if(len(game) == 0):
            return abort(404)
        else:
            #select game tag
            cur.execute("SELECT tag, count from game_tag where game = %s",(name,))
            tag = [record for record in cur]

            #may need to consider here is there is no tag

            #tag is a nested list with count in tag[][1],reviews is a nest list with k reviews
            return render_template("search.html", name=name, picture=game[0][0], video_link= game[0][1],overall_rating=game[0][2],desciption=game[0][3],platform=game[0][4], \
            tag=tag)




###put search, sort and submit review function here:

#search: input:game name, output:game page
#fuzzy search not implemented, may need further implementation (might have question here)
@app.route('/search', methods=['GET'])
def search():
    #app.logger.info("In search")
    name = request.args.get("name")
    app.logger.info("Search for game %s", name)

    return redirect(url_for("list_game",name=name))


#sort: input:sort method, output:a list of top 10 games
@app.route('/sort', methods=['GET'])
def sort():
    sort_method = request.args.get("method")
    app.logger.info("Sort by method %s", method)
    game_list = []
    with db.get_db_cursor() as cur:
        if sort_method == "rating":
            cur.execute("SELECT name from game order by rating DESC")
            game_list = [record[0] for record in cur]
        elif sort_method == "popularity":
            cur.execute("SELECT name from game order by popularity DESC")
            game_list = [record[0] for record in cur]

    if (len(game_list) > 10):
        game_list = game_list[:10]

    return render_template('main.html', game_list=game_list)
    #redirect(url_for("home", game_list=game_list))


#new review:input-review, return to game page
@app.route('/<string:name>',methods=['POST'])
def new_review(name):
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

    return redirect(url_for('game',name=name))
