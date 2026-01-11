from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import uuid
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecret'

# ---------- DB HELPERS ---------- #
db_conf = dict(host='localhost', user='root', password='', database='flatmgr', cursorclass=pymysql.cursors.DictCursor)

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
    rows = db_read("SELECT id,title,done FROM chores WHERE user_id=%s ORDER BY id DESC", (current_user.id,))
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
    rows = db_read("SELECT id,amount,description,date FROM expenses WHERE user_id=%s ORDER BY id DESC", (current_user.id,))
    return jsonify(rows)

@app.route('/api/expenses', methods=['POST'])
@login_required
def add_expense():
    data = request.json
    db_write("INSERT INTO expenses (user_id,amount,description) VALUES (%s,%s,%s)",
             (current_user.id, data['amount'], data['description']))
    return jsonify(success=True)

@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
@login_required
def delete_expense(eid):
    db_write("DELETE FROM expenses WHERE id=%s AND user_id=%s", (eid, current_user.id))
    return jsonify(success=True)

# ---------- API : GROUP + CREATE / JOIN ---------- #
@app.route('/api/group', methods=['GET'])
@login_required
def get_group():
    rows = db_read("""SELECT u.id,u.username FROM users u
                      JOIN group_members g ON u.id=g.user_id
                      WHERE g.group_id=(SELECT group_id FROM group_members WHERE user_id=%s LIMIT 1)""", (current_user.id,))
    return jsonify(rows)

@app.route('/api/group/create', methods=['POST'])
@login_required
def create_group():
    name = request.json.get('name') or f"{current_user.username}'s Group"
    group_uuid = str(uuid.uuid4())
    db_write("INSERT INTO `groups` (group_name, owner_id, group_uuid) VALUES (%s,%s,%s)",
             (name, current_user.id, group_uuid))
    gid = db_read("SELECT LAST_INSERT_ID() as id")[0]['id']
    db_write("INSERT INTO group_members (group_id,user_id) VALUES (%s,%s)", (gid, current_user.id))
    return jsonify(success=True, group_uuid=group_uuid)

@app.route('/api/group/join', methods=['POST'])
@login_required
def join_group():
    g_uuid = request.json['group_uuid'].strip()
    rows = db_read("SELECT id FROM `groups` WHERE group_uuid=%s", (g_uuid,))
    if not rows:
        return jsonify(success=False, error='Group not found'), 404
    gid = rows[0]['id']
    try:
        db_write("INSERT INTO group_members (group_id,user_id) VALUES (%s,%s)", (gid, current_user.id))
        return jsonify(success=True)
    except pymysql.err.IntegrityError:
        return jsonify(success=False, error='Already member'), 400

@app.route('/api/group/<int:uid>', methods=['DELETE'])
@login_required
def remove_member(uid):
    if uid == current_user.id:
        return jsonify(success=False, error='Cannot remove yourself'), 400
    gid_rows = db_read("SELECT group_id FROM group_members WHERE user_id=%s LIMIT 1", (current_user.id,))
    gid = gid_rows[0]['group_id']
    db_write("DELETE FROM group_members WHERE group_id=%s AND user_id=%s", (gid, uid))
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)