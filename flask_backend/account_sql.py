import sqlite3
import logging
import random
import string
import hashlib
from typing import List, Tuple
from utils.logging_utils import log_set
from utils.exceptions import DuplicateValueError, PasswordError, AccountError


def generate_key(length: int, unused: str = "':;^`(){}[]"):
    """
    length长度的随机密钥, 包含大小写字母、数字、符号
    """
    symbols = "".join([i for i in string.punctuation if i not in unused])
    sr = random.SystemRandom()
    rest = "".join(sr.choice(string.ascii_letters + string.digits + symbols) for _ in range(length - 4))
    mix = f"{sr.choice(string.ascii_lowercase)}{sr.choice(string.ascii_uppercase)}{sr.choice(string.digits)}{sr.choice(symbols)}{rest}"
    return "".join(random.sample(mix, len(mix)))


def get_hex_sha(a_string: str):
    sha256 = hashlib.sha256()
    sha256.update(a_string.encode("utf-8"))
    return sha256.hexdigest()


class AccountSQL:
    """
    该类用来创建一个account数据表
    注，数据库仅存储用户密钥的SHA256的十六进制值，不存储明文密钥，故无法查看新的有效数据。
    请自行记录密钥和用户名对应值
    """

    def __init__(self, sql_name: str = "account.db"):
        self.conn = sqlite3.connect(sql_name)
        self._create_table_if_not_exits()
        self._init_admin_if_not_exits()

    def _create_table_if_not_exits(self):
        """
        如果不存在表account，则创建并初始化
        """
        cursor = self.conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS account (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
            )""")
        self.conn.commit()

    def _init_admin_if_not_exits(self):
        """
        如果不存在权限为admin的账户，则创建默认账户
        """
        cursor = self.conn.cursor()
        if cursor.execute("SELECT COUNT(role) FROM account WHERE role = 'admin';").fetchone()[0] == 0:
            admin_pwd = generate_key(15)
            logging.warning(
                f"未找到admin权限用户,使用默认值: username: 'admin', password: '{admin_pwd}' 请妥善保管该用户名-密钥对。数据库无法查看")
            cursor.execute("""
                INSERT INTO account (username, password, role, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
                """, ('admin', get_hex_sha(admin_pwd), 'admin', '2023-01-01 00:00:00', '2030-01-01 00:00:00'))
            self.conn.commit()

    def create_accounts(self, account_list: List[Tuple[str, str, str, str, str]]):
        """
        根据账户列表向数据库添加数据
        :param account_list: list or tuple
        """
        cursor = self.conn.cursor()
        # 遍历列表判断username重复项
        for account in account_list:
            if self.check_account_exits(username=account[0]):
                raise DuplicateValueError(f"{account[0]} already exists in the table.")
        for account in account_list:
            logging.warning(f"Successful created: username: '{account[0]}' password: '{account[1]}' role: {account[2]} start_time: {account[3]} end_time: {account[4]}")
            cursor.execute("""
                INSERT INTO account (username, password, role, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
                """, (account[0], get_hex_sha(account[1]), account[2], account[3], account[4]))
        self.conn.commit()

    def check_account_exits(self, username: str) -> bool:
        """
        判断数据库内是否存在该用户
        """
        cursor = self.conn.cursor()
        if cursor.execute("SELECT COUNT(username) FROM account WHERE username = ?;", [username]).fetchone()[0] != 0:
            return True
        else:
            return False

    def verify_account(self, username: str, password: str) -> tuple:
        """
        根据用户名和密码查询数据库
        """
        password = get_hex_sha(password)
        cursor = self.conn.cursor()
        full_export = cursor.execute('''
            SELECT * FROM account
            WHERE username = ? AND password = ?
            ''', (username, password)).fetchone()
        if full_export is not None:
            return full_export
        else:
            username_export = cursor.execute('''
                SELECT * FROM account
                WHERE username = ?
                ''', (username,)).fetchone()
            if username_export is not None:
                raise PasswordError(f"{username}'s password wrong")
            else:
                raise AccountError(f"{username} not found")


if __name__ == '__main__':
    log_set(logging.INFO, False)
    sql = AccountSQL("account.db")

