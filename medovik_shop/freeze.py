from flask_frozen import Freezer
from app import app

freezer = Freezer(app)

# Список всех страниц, которые нужно сгенерировать
@freezer.register_generator
def generate_pages():
    # Главная страница
    yield '/'
    
    # Категории
    for category in ['мёд', 'прополис', 'воск', 'другое']:
        yield f'/category/{category}'
    
    # Все товары из базы
    from database import Database
    db = Database()
    for product in db.get_all_products():
        yield f'/product/{product["id"]}'
    
    # Другие страницы
    yield '/login'
    yield '/register'
    yield '/cart'
    yield '/checkout'
    yield '/profile'
    
    # Админка
    yield '/admin'
    yield '/admin/products'
    yield '/admin/orders'
    yield '/admin/users'

if __name__ == '__main__':
    freezer.freeze()
