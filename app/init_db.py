from app import db, create_app
from app.models import CommonIngredient

def init_common_ingredients():
    common_ingredients = [
        {"name": "🧂 盐", "unit": "适量", "order": 0},
        {"name": "🧄 蒜", "unit": "两瓣", "order": 1},
        {"name": "🫚 姜", "unit": "适量", "order": 2},
        {"name": "🌱小葱", "unit": "适量", "order": 3},
        {"name": "🍶 生抽", "unit": "适量", "order": 4},
        {"name": "🍶蚝油", "unit": "适量", "order": 5},
        {"name": "🍶 料酒", "unit": "适量", "order": 6},
        {"name": "🍶醋", "unit": "适量", "order": 7},
        {"name": "🧂白糖", "unit": "适量", "order": 8},
        {"name": "🧂味精", "unit": "适量", "order": 9},
        {"name": "🫙淀粉", "unit": "适量", "order": 10},
        {"name": "🫙胡椒粉", "unit": "适量", "order": 11},
        {"name": "🌶️辣椒", "unit": "适量", "order": 12},
        {"name": "🥬大葱", "unit": "适量", "order": 13},
        {"name": "🧅洋葱", "unit": "适量", "order": 14}
    ]

    # 检查是否已有数据
    if CommonIngredient.query.first() is None:
        for ing in common_ingredients:
            ingredient = CommonIngredient(
                name=ing["name"],
                unit=ing["unit"],
                order=ing["order"]
            )
            db.session.add(ingredient)
        
        db.session.commit()
        print("常见食材初始化完成")
    else:
        print("常见食材数据已存在，跳过初始化")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        init_common_ingredients() 