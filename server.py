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
    return "We don't have this game in our database"

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
    app.logger.info("Return URL is %s",request.referrer)
    session['return_url'] = request.referrer

    params = { 'returnTo': url_for('callback2', _external=True), 'client_id': os.environ['AUTH0_CLIENT_ID'] }
    # params = { 'returnTo': url_for('home', _external=True), 'client_id': os.environ['AUTH0_CLIENT_ID'] }
    return redirect(auth0().api_base_url + '/v2/logout?' + urlencode(params))


@app.route('/callback2')
def callback2():
    return redirect(session['return_url'])


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
        avatar = session['profile']["picture"]
    else:
        signin = False
        avatar = None

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
        cur.execute("SELECT * from review, reviewer, game where review.reviewer_id=reviewer.id and review.game_id = game.id order by timestamp DESC limit %s",(k,))
        reviews = [record for record in cur]
        app.logger.info("Review is %s",reviews[0])
        # session['search_trie'] = trie.__dict__

    return render_template('main.html',reviews=reviews,rating_game_list=rating_game_list,popularity_game_list=popularity_game_list,signin = signin,avatar = avatar)
        # redirect(url_for('home_trie_search',game_list=game_list,reviews=reviews, trie = trie))


@app.route('/<int:id>', methods=['GET'])
def game(id):
    if 'profile' in session:
        signin = True
        oauth_id = session['profile']['user_id']
        avatar = session['profile']['picture']
    else:
        signin = False
        oauth_id = None
        avatar = None

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
            m = 3
            cur.execute("SELECT * from game_tag, tag where game_id = %s and tag_id=id order by count DESC limit %s" ,(id,m,))
            tags = [record for record in cur]

            #select the most recent k reviews for the game
            k=5
            cur.execute("SELECT * from review, reviewer where game_id = %s and review.reviewer_id=reviewer.id order by timestamp DESC limit %s",(id,k))
            reviews = [record for record in cur]

            #tag is a nested list with count in tag[][1],reviews is a nest list with k reviews
            return render_template("game.html", game=game,tags=tags,reviews=reviews, pictures=pictures,signin = signin,avatar = avatar,oauth_id=oauth_id)

            #return render_template("game.html", name=name, picture=game[0][0], video_link= game[0][1],overall_rating=game[0][2],desciption=game[0][3],platform=game[0][4], \
            #tag=tag,reviewer=review[0],title=review[1],content=review[2],review_rating=review[3])


###put search, sort and submit review function here:

#search: input:game name, output:game page
#fuzzy search and auto-complete not implemented, may need further implementation (might have question here)
@app.route('/search', methods=['GET'])
def search():
    if 'profile' in session:
        signin = True
        avatar = session['profile']["picture"]
    else:
        signin = False
        avatar = None

    with db.get_db_cursor() as cur:
        name = request.args.get("global")
        app.logger.info("Search for game %s", name)
        #first find if game exits in our database and extract game data
        cur.execute("SELECT * from game where name ilike %s", ("%"+name+"%",))
        games = [record for record in cur]
        if(len(games) == 0):
            return abort(404)
        else:

            cur.execute("SELECT * from game order by rating DESC limit 10")
            rating_game_list = [record for record in cur]
            app.logger.info("Inside list is %s %s %s %s %s %s %s %s %s %s",rating_game_list[0][0],rating_game_list[0][1],rating_game_list[0][2],rating_game_list[0][3],rating_game_list[0][4],rating_game_list[0][5],rating_game_list[0][6],rating_game_list[0][7],rating_game_list[0][8],rating_game_list[0][9])
            cur.execute("SELECT * from game order by popularity DESC limit 10")
            popularity_game_list = [record for record in cur]

            return render_template("search.html", games=games,rating_game_list=rating_game_list,popularity_game_list=popularity_game_list,signin = signin,avatar = avatar)


@app.route("/autocomplete", methods=['GET'])
def search_autocomplete():
    if not request.args.get("query"):
        app.logger.info("I am here")
        return jsonify([])

    else:
        query = request.args.get("query")
        app.logger.info("query is %s",query)
        with db.get_db_cursor() as cur:
            trie = Trie()
            cur.execute("SELECT name from game order by popularity DESC")
            trie_game_list = [record[0] for record in cur]
            for i in trie_game_list:
                trie.insert(i)

            app.logger.info("return is %s",list(trie.getData(query)))
            return jsonify(list(trie.getData(query)))



@app.route('/<int:id>', methods=['POST'])
def new_review(id):
    #when I can call this function, I am definitely in session
    oauth_id = session['profile']['user_id']

    title = request.form.get("title")
    description1 = request.form.get("description1")
    description = request.form.get("description")
    rating = request.form.get("rating")
    ts=time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    
    with db.get_db_cursor(True) as cur:

        rid = request.form.get("dr")
        r2id = request.form.get("er")
        app.logger.info(r2id)
        app.logger.info(description1)
        if rid!=None and rid!="":
            #get necessary information before we delete review
            cur.execute("SELECT game_id, rating from review where id = %s",(rid,))
            game_id = [record[0] for record in cur][0]
            cur.execute("SELECT game_id, rating from review where id = %s",(rid,))
            rating = [record[1] for record in cur][0]

            #delete review
            cur.execute("DELETE FROM review WHERE id=%s;",(rid,))

            #update overallrating
            cur.execute("SELECT rating, review_number from game where id = %s",(game_id,))
            overall_rating = [record[0] for record in cur][0]
            cur.execute("SELECT rating, review_number from game where id = %s",(game_id,))
            review_number = [record[1] for record in cur][0]
            app.logger.info("data is %s,%s,%s,%s",game_id,rating,overall_rating,review_number)
            if review_number == 1:
                overall_rating = 0
            else:
                overall_rating = round((overall_rating*review_number - rating)/(review_number-1),2)
            cur.execute("UPDATE game set rating = %s, review_number = %s where id = %s",(overall_rating,review_number-1,game_id,))
            # cur.execute("UPDATE game set rating = %s, review_number = %s where id = %s",(overall_rating,review_number+1,id,))

        #update overall rating in game table
        elif rating != None and rating != "":
            cur.execute("SELECT rating, review_number from game where id = %s",(id,))
            overall_rating = [record[0] for record in cur][0]
            cur.execute("SELECT rating, review_number from game where id = %s",(id,))
            review_number = [record[1] for record in cur][0]
            overall_rating = round((overall_rating*review_number + int(rating))/(review_number+1),2)
            cur.execute("UPDATE game set rating = %s, review_number = %s where id = %s",(overall_rating,review_number+1,id,))

        if title!="" and title!=None:
            cur.execute("SELECT id from reviewer where oauth_id = %s",(oauth_id,))
            reviewer_id=[record[0] for record in cur][0]
            cur.execute("INSERT INTO review (reviewer_id, game_id, timestamp, title, content, rating) VALUES (%s, %s, %s, %s, %s, %s);", (reviewer_id,id, timestamp, title, description,rating,))

        if r2id!=None and r2id!="":
            cur.execute("UPDATE review set content = %s where id = %s",(description1,r2id,))


        #update tag, tags is a string contains tag
        tags = request.form.get("tag")
        if tags!=None and tags !="":
            cur.execute("SELECT tag_id, count, name from game_tag, tag where game_id = %s and id=tag_id",(id,))
            exist_tag_id = [record[0] for record in cur]
            cur.execute("SELECT tag_id, count, name from game_tag, tag where game_id = %s and id=tag_id",(id,))
            tag_count = [record[1] for record in cur]
            cur.execute("SELECT tag_id, count, name from game_tag, tag where game_id = %s and id=tag_id",(id,))
            exist_tag_name = [record[2] for record in cur]
            cur.execute("SELECT count(id) from tag")
            num_tag=[record[0] for record in cur][0]
            tag_index=-1

            tag_list = tags.split()
            for tag in tag_list:
                app.logger.info("Tag is %s",tag)
                if tag in exist_tag_name:
                    app.logger.info("hello")
                    tag_index = exist_tag_name.index(tag)
                    new_count = tag_count[tag_index] + 1
                    cur.execute("UPDATE game_tag set count = %s where game_id = %s and tag_id = %s",(new_count,id,exist_tag_id[tag_index],))
                else:
                    new_count = 1
                    cur.execute("INSERT INTO tag (id,name) values (%s,%s)",(num_tag+1,tag,))
                    cur.execute("INSERT INTO game_tag (game_id,tag_id,count) values (%s,%s,%s)",(id,num_tag+1,new_count,))
                    num_tag = num_tag +1;

        return redirect(url_for("game", id=id))


@app.route('/verifyreviewer', methods=['GET'])
@require_auth
def verifyreviewer():
    id = request.form.get("")
    return redirect(url_for("game", id=id))
