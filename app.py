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

    funny_fakes = [
        "Sleeping 24/7 😴🛌",
        "Eating garbage like a raccoon 🦝🗑️",
        "Crying over a bug in the code 😭💻",
        "Getting abducted by aliens 👽🛸",
        "Becoming a full-time meme 🤡📉",
        "Talking to walls 🧱🗣️",
        "Forgetting my own name 🤔🚪",
        "Spilling hot tea on myself ☕🔥",
        "Running away to the mountains 🏔️🏃‍♀️",
        "Fighting a street dog and losing 🐕🥊",
        "Googling how to be cool 🤓🔍",
        "Being completely useless 🫠🗑️",
        "Dancing on TikTok for views 🕺🤳",
        "Living in a cardboard box 📦🏚️",
        "Trying to fix code with duct tape 🩹🛠️"
    ]

    for item in quiz_data:
        ans_value = item['answer']
        available_fakes = [f for f in funny_fakes if f.lower().strip() != ans_value.lower().strip()]
        fakes = random.sample(available_fakes, min(3, len(available_fakes)))
        
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
