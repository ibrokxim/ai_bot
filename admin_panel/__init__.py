import pymysql

# Исправляем проблему совместимости PyMySQL с Python 3.12
pymysql.VERSION = (1, 4, 0, "final", 0)

# Указываем Django использовать PyMySQL вместо mysqlclient
pymysql.install_as_MySQLdb()

