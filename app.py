import sqlite3
import uuid
import json
import random
from flask import Flask, render_template, request, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this'
DATABASE = 'matequiz.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quizzes (
                quiz_id TEXT PRIMARY KEY,
                creator_name TEXT NOT NULL,
                answers TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id TEXT NOT NULL,
                friend_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                max_score INTEGER NOT NULL,
                FOREIGN KEY (quiz_id) REFERENCES quizzes (quiz_id)
            )
        ''')
        db.commit()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['GET', 'POST'])
def create_quiz():
    if request.method == 'POST':
        creator_name = request.form.get('creator_name', '').strip()
        if not creator_name:
            flash('Please enter your name! 👑', 'error')
            return redirect(url_for('create_quiz'))
        
        quiz_data = []
        for i in range(1, 11):
            q_text = request.form.get(f'q{i}_text', '').strip()
            q_ans = request.form.get(f'q{i}_ans', '').strip()
            
            if q_text and q_ans:
                quiz_data.append({"question": q_text, "answer": q_ans})

        if len(quiz_data) < 3:
            flash('Please fill out at least 3 questions and answers! ⚠️', 'error')
            return redirect(url_for('create_quiz'))

        quiz_id = str(uuid.uuid4())[:8]

        db = get_db()
        db.execute('INSERT INTO quizzes (quiz_id, creator_name, answers) VALUES (?, ?, ?)',
                   (quiz_id, creator_name, json.dumps(quiz_data)))
        db.commit()

        return redirect(url_for('share_quiz', quiz_id=quiz_id))

    return render_template('create.html')

@app.route('/quiz/<quiz_id>/share')
def share_quiz(quiz_id):
    db = get_db()
    quiz = db.execute('SELECT * FROM quizzes WHERE quiz_id = ?', (quiz_id,)).fetchone()
    if not quiz:
        return "Quiz not found!", 404
    
    quiz_url = request.host_url + f'quiz/{quiz_id}'
    return render_template('share.html', quiz=quiz, quiz_url=quiz_url)

@app.route('/quiz/<quiz_id>', methods=['GET', 'POST'])
def take_quiz(quiz_id):
    db = get_db()
    quiz = db.execute('SELECT * FROM quizzes WHERE quiz_id = ?', (quiz_id,)).fetchone()
    if not quiz:
        return "Quiz not found!", 404

    quiz_data = json.loads(quiz['answers'])

    for item in quiz_data:
        q_lower = item['question'].lower()
        ans_value = item['answer']
        
        # --- SMART REALISTIC CATEGORY LOGIC ---
        fakes_dict = {
            "food": {
                "keywords": ["food", "eat", "drink", "meal", "coffee", "tea", "snack", "hungry", "dish", "breakfast", "lunch", "dinner"],
                "options": ["Biryani 🍛", "Maggi 🍜", "Pizza 🍕", "Pasta 🍝", "Momo 🥟", "Burger 🍔", "Ice cream 🍦", "Fries 🍟", "Chocolates 🍫"]
            },
            "color": {
                "keywords": ["color", "wear", "closet", "outfit", "dress", "clothes", "shade"],
                "options": ["Black 🖤", "Blue 💙", "Red ❤️", "White 🤍", "Purple 💜", "Yellow 💛", "Green 💚", "Brown 🤎"]
            },
            "travel": {
                "keywords": ["travel", "city", "country", "place", "go", "visit", "teleport", "vacation", "trip"],
                "options": ["Goa 🏖️", "Paris 🗼", "Maldives 🏝️", "Mountains ⛰️", "London 🎡", "Japan 🗾", "Dubai 🏙️", "Switzerland 🏔️"]
            },
            "hobby": {
                "keywords": ["sunday", "free time", "hobby", "do", "spend", "weekend", "day", "bored", "habit"],
                "options": ["Sleeping 😴", "Watching Netflix 🎬", "Scrolling Instagram 📱", "Listening to music 🎧", "Reading books 📚", "Gaming 🎮", "Shopping 🛍️", "Coding 💻"]
            },
            "music": {
                "keywords": ["song", "music", "listen", "artist", "singer", "band", "playlist", "genre"],
                "options": ["Taylor Swift 🎤", "Arijit Singh 🎸", "BTS 💜", "The Weeknd 🎧", "Darshan Raval 🎶", "Ed Sheeran 🎸", "Hip-hop 🎧", "K-Pop 🎶"]
            },
            "movie": {
                "keywords": ["movie", "show", "series", "watch", "actor", "actress", "marvel", "anime", "cinema"],
                "options": ["Friends 🛋️", "Stranger Things 🚲", "Marvel Movies 🦸‍♂️", "Anime 🌸", "Harry Potter ⚡", "K-Dramas 📺", "Horror movies 👻"]
            },
            "number": {
                "keywords": ["how many", "age", "year", "date", "time", "number", "alarms", "hours"],
                "options": ["1", "2", "3", "4", "5", "10", "Zero", "Too many to count"]
            }
        }
        
        # ডিফল্ট অপশন (যদি প্রশ্নের সাথে কোনো ক্যাটাগরি না মেলে)
        generic_fakes = [
            "Yes 👍", "No 👎", "Maybe 🤔", "Depends on the mood 🎭", 
            "Both A and B 🧐", "None of the above 🤷‍♀️", "Not sure 🤐", 
            "That's a secret 🤫"
        ]
        
        # ক্যাটাগরি খোঁজার চেষ্টা
        selected_fakes = generic_fakes
        for category, data in fakes_dict.items():
            if any(kw in q_lower for kw in data["keywords"]):
                selected_fakes = data["options"]
                break
                
        # আসল উত্তরের সাথে যেন হুবহু মিলে না যায়
        available_fakes = [f for f in selected_fakes if f.lower().strip() != ans_value.lower().strip()]
        
        # যদি কোনো কারণে ৩টি অপশন না থাকে, তখন অন্যান্য লিস্ট থেকে ধার করবে
        if len(available_fakes) < 3:
            fallback = [f for f in generic_fakes if f.lower().strip() != ans_value.lower().strip() and f not in available_fakes]
            available_fakes.extend(fallback)
            
        # র‍্যান্ডম ৩টি অপশন সিলেক্ট করা
        fakes = random.sample(available_fakes, min(3, len(available_fakes)))
        
        # আসল উত্তর এবং ৩টি ভুল অপশন একসাথে করা
        options = [ans_value] + fakes
        random.shuffle(options)
        item['options'] = options

    if request.method == 'POST':
        friend_name = request.form.get('friend_name', '').strip()
        if not friend_name:
            flash('Please enter your name! 🤡', 'error')
            return redirect(url_for('take_quiz', quiz_id=quiz_id))

        score = 0
        total = len(quiz_data)
        
        for index, item in enumerate(quiz_data):
            friend_ans = request.form.get(f'ans_{index}')
            if friend_ans and friend_ans.strip().lower() == item['answer'].strip().lower():
                score += 1

        db.execute('INSERT INTO submissions (quiz_id, friend_name, score, max_score) VALUES (?, ?, ?, ?)',
                   (quiz_id, friend_name, score, total))
        db.commit()

        return redirect(url_for('scoreboard', quiz_id=quiz_id, friend_name=friend_name, score=score))

    return render_template('take.html', quiz=quiz, quiz_data=quiz_data)

@app.route('/quiz/<quiz_id>/scoreboard')
def scoreboard(quiz_id):
    db = get_db()
    quiz = db.execute('SELECT * FROM quizzes WHERE quiz_id = ?', (quiz_id,)).fetchone()
    if not quiz:
        return "Quiz not found!", 404

    scores = db.execute('SELECT * FROM submissions WHERE quiz_id = ? ORDER BY score DESC, id ASC', (quiz_id,)).fetchall()
    
    recent_friend = request.args.get('friend_name')
    recent_score = request.args.get('score')

    return render_template('scoreboard.html', quiz=quiz, scores=scores, recent_friend=recent_friend, recent_score=recent_score)

if __name__ == '__main__':
    app.run(debug=True)
