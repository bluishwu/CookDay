from app import create_app, db
from app.init_db import init_common_ingredients

app = create_app()

# 在应用上下文中初始化数据库和常用食材
with app.app_context():
    db.create_all()
    init_common_ingredients()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 