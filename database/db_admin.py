import sqlite3


def sql_start():
    global base, cur
    base = sqlite3.connect(r"database\users.db")
    cur = base.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users(user_id PRIMARY KEY, user_name TEXT, promise TEXT, deadline date )")
    base.commit()


def deadline_check(user_id):
    cur.execute(f"SELECT user_id, deadline FROM users ")
    results = cur.fetchall()
    for i in results:
        user = str(i[0])
        deadline = str(i[1])
    return user, deadline


def check_info():
    cur.execute(f"SELECT user_id, deadline FROM users ")
    results = cur.fetchall()
    return results


def check_promise(user_id):
    cur.execute(f"SELECT promise FROM users WHERE user_id = {user_id}")
    result = cur.fetchone()
    return result


def check_email():
    cur.execute(f"SELECT email from users")
    result = cur.fetchall()
    return result


async def sql_add(data):
    cur.execute("INSERT OR IGNORE INTO users (user_id, user_name, promise, deadline) VALUES (?, ?, ?, ?)",
                [data['user_id'], data['user_name'], data['promise'], data['deadline']])
    base.commit()


async def sql_add_email(data, user_id):
    cur.execute(f"UPDATE users SET email = '{data['email']}' WHERE user_id = {user_id} ")
    base.commit()


def all_users():
    cur.execute("SELECT user_id, user_name from users ")
    return cur.fetchall()


def sql_deadline(user_id):
    cur.execute(f"SELECT deadline from users where user_id = {user_id}")
    return cur.fetchone()


def sql_delete(user_id):
    cur.execute(f"DELETE from users WHERE user_id ={user_id}")
    base.commit()


def check_user(user_id):
    cur.execute(f"SELECT * FROM users where user_id ={user_id}")
    res = cur.fetchone()
    return res
