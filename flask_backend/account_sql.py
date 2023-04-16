import sqlite3


class AccountSQL:
    def __init__(self, sql_name: str = "account.db"):
        self.conn = sqlite3.connect(sql_name)
        self._create_table()
        self._init_admin()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS account (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL
        )""")
        self.conn.commit()

    def _init_admin(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO account (user_id, username, password, role, start_time, end_time)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (0, 'admin', 'password', 'admin', '2023-01-01 00:00:00', '2030-01-01 00:00:00'))
        self.conn.commit()


if __name__ == '__main__':
    sql = AccountSQL("account.db")


# """SELECT * FROM account WHERE username = {username} AND password = {password}"""
