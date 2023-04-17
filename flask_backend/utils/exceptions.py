class DuplicateValueError(Exception):
    """
    数据库内已存在重复值
    """
    pass


class PasswordError(Exception):
    """
    密码错误
    """
    pass


class AccountError(Exception):
    """
    账户和密码不存在
    """
    pass
