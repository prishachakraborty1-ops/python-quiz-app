import sqlite3
import uuid
import json
from flask import Flask, render_template, request, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-this'
DATABASE = 'matequiz.db'

# Predefined Questions
DEFAULT_QUESTIONS = [
    {
        "id": 1,
        "question": "What is my ideal weekend activity?",
        "options": ["Binge-watching shows", "Outdoor adventure", "Gaming all night", "Hanging out with friends"]
    },
    {
        "id": 2,
        "question": "Which superpower would I pick?",
        "options": ["Invisibility", "Flight", "Teleportation", "Mind Reading"]
    },
    {
        "id": 3,
        "question": "What is my go-to comfort food?",
        "options": ["Pizza", "Burgers", "Ice Cream", "Ramen"]
    },
    {
        "id": 4,
        "question": "Where would I love to go on vacation?",
        "options": ["Tropical Beach", "Historic European City", "Mountain Cabin", "Bustling Tokyo"]
    },
    {
        "id": 5,
        "question": "Are you a morning person or night owl?",
        "options": ["Night Owl 🦉", "Early Bird 🌅", "Depends on coffee ☕", "Permanently exhausted 😴"]
    }
]

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
            flash('Please enter your name!', 'error')
            return redirect(url_for('create_quiz'))

        answers = {}
        for q in DEFAULT_QUESTIONS:
            answer = request.form.get(f'q_{q["id"]}')
            if not answer:
                flash(f'Please answer Question {q["id"]}!', 'error')
                return redirect(url_for('create_quiz'))
            answers[str(q['id'])] = answer

        quiz_id = str(uuid.uuid4())[:8]

        db = get_db()
        db.execute('INSERT INTO quizzes (quiz_id, creator_name, answers) VALUES (?, ?, ?)',
                   (quiz_id, creator_name, json.dumps(answers)))
        db.commit()

        return redirect(url_for('share_quiz', quiz_id=quiz_id))

    return render_template('create.html', questions=DEFAULT_QUESTIONS)

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

    correct_answers = json.loads(quiz['answers'])

    if request.method == 'POST':
        friend_name = request.form.get('friend_name', '').strip()
        if not friend_name:
            flash('Please enter your name!', 'error')
            return redirect(url_for('take_quiz', quiz_id=quiz_id))

        score = 0
        total = len(DEFAULT_QUESTIONS)
        for q in DEFAULT_QUESTIONS:
            friend_ans = request.form.get(f'q_{q["id"]}')
            if friend_ans == correct_answers.get(str(q['id'])):
                score += 1

        db.execute('INSERT INTO submissions (quiz_id, friend_name, score, max_score) VALUES (?, ?, ?, ?)',
                   (quiz_id, friend_name, score, total))
        db.commit()

        return redirect(url_for('scoreboard', quiz_id=quiz_id, friend_name=friend_name, score=score))

    return render_template('take.html', quiz=quiz, questions=DEFAULT_QUESTIONS)

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
    @app.route('/create', methods=['GET', 'POST'])
def create_quiz():
    if request.method == 'POST':
        creator_name = request.form.get('creator_name', '').strip()
        
        # Collect custom questions and answers
        quiz_data = []
        for i in range(1, 4):
            q_text = request.form.get(f'q{i}_text')
            q_ans = request.form.get(f'q{i}_ans')
            if q_text and q_ans:
                quiz_data.append({"question": q_text, "answer": q_ans.lower().strip()})

        quiz_id = str(uuid.uuid4())[:8]

        db = get_db()
        # We store the entire quiz_data array inside the 'answers' column as JSON
        db.execute('INSERT INTO quizzes (quiz_id, creator_name, answers) VALUES (?, ?, ?)',
                   (quiz_id, creator_name, json.dumps(quiz_data)))
        db.commit()

        return redirect(url_for('share_quiz', quiz_id=quiz_id))

    return render_template('create.html')
