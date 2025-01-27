from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os
from flask_login import LoginManager

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = 'main.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 初始化数据库
    db.init_app(app)

    # 初始化Flask-Login
    login_manager.init_app(app)

    # 注册蓝图
    from app.routes import main
    app.register_blueprint(main)

    # 创建数据库表
    with app.app_context():
        db.create_all()

    return app 