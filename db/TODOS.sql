-- 1. USERS
CREATE TABLE users (
    id       INTEGER PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255)       NOT NULL
);

-- 2. GROUPS (with owner + unique UUID)
CREATE TABLE `groups` (
    id         INTEGER PRIMARY KEY AUTO_INCREMENT,
    group_name VARCHAR(100) NOT NULL,
    owner_id   INTEGER,
    group_uuid CHAR(36) UNIQUE NOT NULL
);

-- 3. USER <-> GROUP
CREATE TABLE group_members (
    group_id INTEGER,
    user_id  INTEGER,
    PRIMARY KEY (group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES `groups`(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)  REFERENCES users(id)   ON DELETE CASCADE
);

-- 4. CHORES
CREATE TABLE chores (
    id       INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id  INTEGER NOT NULL,
    title    VARCHAR(200) NOT NULL,
    done     BOOLEAN DEFAULT 0,
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
    id          INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id     INTEGER NOT NULL,
    amount      DECIMAL(10,2) NOT NULL,
    description VARCHAR(200),
    date        DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);