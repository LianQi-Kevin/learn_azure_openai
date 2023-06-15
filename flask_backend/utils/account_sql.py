import hashlib
import logging
import random
import re
import sqlite3
import string
from datetime import datetime
from typing import List, Tuple

from utils.exceptions import DuplicateValueError, PasswordError, AccountError, TimeSetError
from utils.logging_utils import log_set


def verify_time(start_time: str, end_time: str) -> Tuple[bool, bool]:
    """
    :param start_time: account allow start time
    :param end_time: account allow end time
    :return: end_time > start_time, end_time > now_time > start_time
    """
    try:
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        return end_time > start_time, end_time > datetime.now() > start_time
    except ValueError:
        raise TimeSetError("datatime.strptime error")


def verify_password(password: str) -> bool:
    pattern = "^(?=.*\\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()_+])[a-zA-Z\\d!@#$%^&*()_+]{8,}$"
    if re.match(pattern, password):
        return True
    else:
        return False


def generate_key(length: int):
    """
    length长度的随机密钥, 包含大小写字母、数字、符号
    """
    symbols = "!@#$%^&*()_+"
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

    def __init__(self, sql_name: str = "account.db", plaintext_pwd: bool = False, admin_username: str = "admin",
                 admin_password: str = generate_key(15)):
        # 是否明文存储密码
        self.plaintext_password = plaintext_pwd

        # todo: 暂时设置check_same_thread=false来规避sqlite3不允许多线程操作的错误，后期需要重构数据库函数封装逻辑来解决
        self.conn = sqlite3.connect(sql_name, check_same_thread=False)
        self._create_table_if_not_exits()
        self._init_admin_if_not_exits(username=admin_username, password=admin_password)

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

    def _init_admin_if_not_exits(self, username: str, password: str):
        """
        如果不存在权限为admin的账户，则创建默认账户
        """
        cursor = self.conn.cursor()
        if cursor.execute("SELECT COUNT(role) FROM account WHERE role = 'admin';").fetchone()[0] == 0:
            logging.warning(
                f"未找到admin权限用户,使用默认值: username: '{username}', password: '{password}' 请妥善保管该用户名-密钥对")
            password = password if self.plaintext_password else get_hex_sha(password)
            cursor.execute("""
                INSERT INTO account (username, password, role, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
                """, (username, password, 'admin', '2023-01-01 00:00:00', '2030-01-01 00:00:00'))
            self.conn.commit()

    def create_accounts(self, account_list: List[Tuple[str, str, str, str, str]]):
        """
        根据账户列表向数据库添加数据
        :param account_list: List[Tuple(username, password, role, start_time, end_time)]
        """
        cursor = self.conn.cursor()
        # 遍历列表判断username重复项
        for account in account_list:
            if self.check_username_exits(account[0]):
                raise DuplicateValueError(f"{account[0]} already in used.")
            if not verify_time(account[3], account[4])[0]:
                raise TimeSetError(f"{account[0]} time set error, {account[4]} early than {account[3]}")
        for account in account_list:
            logging.warning(
                f"Successful created: username: '{account[0]}' password: '{account[1]}' role: '{account[2]}' start_time: '{account[3]}' end_time: '{account[4]}'")
            cursor.execute("""
                INSERT INTO account (username, password, role, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
                """, (account[0], account[1] if self.plaintext_password else get_hex_sha(account[1]),
                      account[2], account[3], account[4]))
        self.conn.commit()

    def check_username_exits(self, username: str) -> bool:
        """
        Check whether the username exists in the database
        """
        cursor = self.conn.cursor()
        if cursor.execute("SELECT COUNT(username) FROM account WHERE username = ?;", [username]).fetchone()[0] != 0:
            return True
        else:
            return False

    def user_id_get_base_info(self, user_id: int) -> Tuple[int, str, str, str]:
        """
        :param user_id: user_id
        :return: Tuple[user_name, role, start_time, end_time]
        """
        cursor = self.conn.cursor()
        item = cursor.execute("SELECT * FROM account WHERE user_id = ?;", [user_id]).fetchone()
        if item is not None:
            return item[1], item[3], item[4], item[5]
        else:
            raise AccountError(f"{user_id} not exits")

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

    def change_password(self, username: str, new_pwd: str):
        """
        根据用户名修改密码
        """

        cursor = self.conn.cursor()
        cursor.execute("UPDATE account SET password = ? WHERE username = ?;",
                       (new_pwd if self.plaintext_password else get_hex_sha(new_pwd), username))
        self.conn.commit()

    def update_allow_time(self, username: str, start_time: str, end_time: str):
        """
        根据用户名修改可用时间
        """
        if self.check_username_exits(username):
            if verify_time(start_time, end_time)[0]:
                cursor = self.conn.cursor()
                cursor.execute("UPDATE account SET start_time = ? and end_time = ? WHERE username = ?;",
                               (start_time, end_time, username))
                self.conn.commit()
            else:
                raise TimeSetError(f"Error, {end_time} early than {start_time}")
        else:
            raise AccountError(f"{username} does not exits")

    def delete_account(self, username: str):
        if self.check_username_exits(username):
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM account WHERE username = ?", [username])
            self.conn.commit()
        else:
            raise AccountError(f"{username} does not exits")


if __name__ == '__main__':
    log_set(logging.INFO, False)
    sql = AccountSQL(sql_name="account.db")
