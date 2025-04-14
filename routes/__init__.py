"""
Инициализация маршрутов API
"""

from flask import Blueprint

# Создаем основной блюпринт для API
api_blueprint = Blueprint('api', __name__)

# Импортируем все маршруты
from .plans import plans_bp
from .requests import requests_bp

# Регистрируем блюпринты
api_blueprint.register_blueprint(plans_bp, url_prefix='/plans')
# Маршруты requests_bp регистрируются в файле requests.py 