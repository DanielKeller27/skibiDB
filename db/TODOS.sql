-- 1. USERS
CREATE TABLE users (
    id       INTEGER PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255)       NOT NULL
);

-- 2. GROUP MEMBERS (simple name list per user)
CREATE TABLE group_members (
    id       INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id  INTEGER NOT NULL,
    name     VARCHAR(100) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. CHORES
CREATE TABLE chores (
    id       INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id  INTEGER NOT NULL,
    title    VARCHAR(200) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. GROCERIES
CREATE TABLE groceries (
    id       INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id  INTEGER NOT NULL,
    name     VARCHAR(200) NOT NULL,
    bought   BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. FINANCES
CREATE TABLE expenses (
    id              INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id         INTEGER NOT NULL,
    group_member_id INTEGER NOT NULL,
    amount          DECIMAL(10,2) NOT NULL,
    description     VARCHAR(200),
    date            DATE DEFAULT (CURRENT_DATE),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (group_member_id) REFERENCES group_members(id) ON DELETE CASCADE
);

-- 7. ASSIGNMENTS (assign a chore to a group member)
CREATE TABLE assignments (
    id              INTEGER PRIMARY KEY AUTO_INCREMENT,
    chore_id        INTEGER NOT NULL,
    group_member_id INTEGER NOT NULL,
    due_date        DATE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chore_id)        REFERENCES chores(id) ON DELETE CASCADE,
    FOREIGN KEY (group_member_id) REFERENCES group_members(id) ON DELETE CASCADE
);