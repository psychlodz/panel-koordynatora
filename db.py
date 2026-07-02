import oracledb


def create_connection(user: str, password: str, dsn: str):
    return oracledb.connect(user=user, password=password, dsn=dsn)
