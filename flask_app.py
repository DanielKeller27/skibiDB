from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import uuid
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecret'

# ---------- DB HELPERS ---------- #
db_conf = dict(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_DATABASE', 'skibidb'),
    cursorclass=pymysql.cursors.DictCursor
)

def db_write(sql, args=()):
    with pymysql.connect(**db_conf) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
        conn.commit()

def db_read(sql, args=()):
    with pymysql.connect(**db_conf) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()

# ---------- AUTH ---------- #
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    rows = db_read("SELECT id,username FROM users WHERE id=%s", (user_id,))
    return User(rows[0]['id'], rows[0]['username']) if rows else None

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        rows = db_read("SELECT id,password FROM users WHERE username=%s", (username,))
        if rows and check_password_hash(rows[0]['password'], password):
            login_user(User(rows[0]['id'], username))
            return redirect(url_for('home'))
        return render_template('home.html', page='login', error='Wrong credentials')
    return render_template('home.html', page='login')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    hashed = generate_password_hash(password)
    try:
        db_write("INSERT INTO users (username,password) VALUES (%s,%s)", (username, hashed))
        uid = db_read("SELECT id FROM users WHERE username=%s", (username,))[0]['id']
        # create personal group
        group_uuid = str(uuid.uuid4())
        db_write("INSERT INTO `groups` (group_name, owner_id, group_uuid) VALUES (%s,%s,%s)",
                 (f"{username}'s Group", uid, group_uuid))
        gid = db_read("SELECT LAST_INSERT_ID() as id")[0]['id']
        db_write("INSERT INTO group_members (group_id,user_id) VALUES (%s,%s)", (gid, uid))
        return redirect(url_for('login'))
    except pymysql.err.IntegrityError:
        return render_template('home.html', page='register', error='Username exists')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---------- DASHBOARD ---------- #
@app.route('/')
@login_required
def home():
    return render_template('home.html', page='dashboard', current_user=current_user)

# ---------- API : CHORES ---------- #
@app.route('/api/chores', methods=['GET'])
@login_required
def get_chores():
    rows = db_read("""
        SELECT c.id, c.title, c.done, gm.name as assigned_to
        FROM chores c
        LEFT JOIN assignments a ON c.id = a.chore_id
        LEFT JOIN group_members gm ON a.group_member_id = gm.id
        WHERE c.user_id=%s 
        ORDER BY c.id DESC
    """, (current_user.id,))
    return jsonify(rows)

@app.route('/api/chores', methods=['POST'])
@login_required
def add_chore():
    title = request.json['title']
    db_write("INSERT INTO chores (user_id,title,done) VALUES (%s,%s,0)", (current_user.id, title))
    return jsonify(success=True)

@app.route('/api/chores/<int:cid>', methods=['PUT'])
@login_required
def toggle_chore(cid):
    db_write("UPDATE chores SET done=NOT done WHERE id=%s AND user_id=%s", (cid, current_user.id))
    return jsonify(success=True)

@app.route('/api/chores/<int:cid>', methods=['DELETE'])
@login_required
def delete_chore(cid):
    db_write("DELETE FROM chores WHERE id=%s AND user_id=%s", (cid, current_user.id))
    return jsonify(success=True)

# ---------- API : GROCERIES ---------- #
@app.route('/api/groceries', methods=['GET'])
@login_required
def get_groceries():
    rows = db_read("SELECT id,name,bought FROM groceries WHERE user_id=%s ORDER BY id DESC", (current_user.id,))
    return jsonify(rows)

@app.route('/api/groceries', methods=['POST'])
@login_required
def add_grocery():
    name = request.json['name']
    db_write("INSERT INTO groceries (user_id,name,bought) VALUES (%s,%s,0)", (current_user.id, name))
    return jsonify(success=True)

@app.route('/api/groceries/<int:gid>', methods=['PUT'])
@login_required
def toggle_grocery(gid):
    db_write("UPDATE groceries SET bought=NOT bought WHERE id=%s AND user_id=%s", (gid, current_user.id))
    return jsonify(success=True)

@app.route('/api/groceries/<int:gid>', methods=['DELETE'])
@login_required
def delete_grocery(gid):
    db_write("DELETE FROM groceries WHERE id=%s AND user_id=%s", (gid, current_user.id))
    return jsonify(success=True)

# ---------- API : EXPENSES ---------- #
@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    rows = db_read("""
        SELECT e.id, e.amount, e.description, e.date, gm.name as member_name
        FROM expenses e
        JOIN group_members gm ON e.group_member_id = gm.id
        WHERE e.user_id=%s ORDER BY e.id DESC
    """, (current_user.id,))
    return jsonify(rows)

@app.route('/api/expenses', methods=['POST'])
@login_required
def add_expense():
    data = request.json
    db_write("INSERT INTO expenses (user_id, group_member_id, amount, description) VALUES (%s,%s,%s,%s)",
             (current_user.id, data['group_member_id'], data['amount'], data['description']))
    return jsonify(success=True)

@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
@login_required
def delete_expense(eid):
    db_write("DELETE FROM expenses WHERE id=%s AND user_id=%s", (eid, current_user.id))
    return jsonify(success=True)

# ---------- API : GROUP MEMBERS ---------- #
@app.route('/api/group', methods=['GET'])
@login_required
def get_group():
    rows = db_read("SELECT id, name FROM group_members WHERE user_id=%s ORDER BY id DESC", (current_user.id,))
    return jsonify(rows)

@app.route('/api/group', methods=['POST'])
@login_required
def add_group_member():
    name = request.json['name']
    db_write("INSERT INTO group_members (user_id, name) VALUES (%s, %s)", (current_user.id, name))
    return jsonify(success=True)

@app.route('/api/group/<int:mid>', methods=['DELETE'])
@login_required
def remove_member(mid):
    db_write("DELETE FROM group_members WHERE id=%s AND user_id=%s", (mid, current_user.id))
    return jsonify(success=True)

# ---------- API : ASSIGNMENTS ---------- #
@app.route('/api/assignments', methods=['GET'])
@login_required
def get_assignments():
    """Get all assignments for the current user."""
    rows = db_read("""
        SELECT a.id, a.chore_id, c.title as chore_title, a.group_member_id, gm.name as assigned_to_name,
               a.due_date, a.created_at
        FROM assignments a
        JOIN chores c ON a.chore_id = c.id
        JOIN group_members gm ON a.group_member_id = gm.id
        WHERE c.user_id = %s
        ORDER BY a.created_at DESC
    """, (current_user.id,))
    return jsonify(rows)

@app.route('/api/assignments', methods=['POST'])
@login_required
def add_assignment():
    """Assign a chore to a group member."""
    data = request.json
    chore_id = data['chore_id']
    group_member_id = data['group_member_id']
    due_date = data.get('due_date')  # optional
    
    db_write(
        "INSERT INTO assignments (chore_id, group_member_id, due_date) VALUES (%s, %s, %s)",
        (chore_id, group_member_id, due_date)
    )
    return jsonify(success=True)

@app.route('/api/assignments/<int:aid>', methods=['DELETE'])
@login_required
def delete_assignment(aid):
    """Delete an assignment."""
    db_write("DELETE FROM assignments WHERE id=%s", (aid,))
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)