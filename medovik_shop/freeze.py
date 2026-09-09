from flask_frozen import Freezer
from app import app
import os

freezer = Freezer(app)

@freezer.register_generator
def generate_pages():
    # Главная
    yield '/'
    
    # Категории
    for category in ['мёд', 'прополис', 'воск', 'другое']:
        yield f'/category/{category}'
    
    # Товары (из базы)
    from database import Database
    db = Database()
    for product in db.get_all_products():
        yield f'/product/{product["id"]}'
    
    # Статические страницы
    yield '/login'
    yield '/register'
    yield '/cart'
    yield '/checkout'
    yield '/profile'
    yield '/admin'
    yield '/admin/products'
    yield '/admin/orders'
    yield '/admin/users'

if __name__ == '__main__':
    # Создаём папку build, если её нет
    if not os.path.exists('build'):
        os.makedirs('build')
    
    # Замораживаем сайт в папку build
    freezer.freeze()
