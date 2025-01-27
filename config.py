import os
from datetime import timedelta

# 调试设置
ENABLE_ERUDA = False

# 站点名称
SITE_NAME = "CookDay"

# 上传文件配置
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 上传文件夹路径
UPLOAD_FOLDER = 'app/static/uploads'

# 数据库配置
SQLALCHEMY_DATABASE_URI = 'sqlite:///recipes.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 密钥配置
SECRET_KEY = 'dev'

# 管理员默认密码
ADMIN_PASSWORD = 'admin'

class Config:
    # 调试模式配置
    ENABLE_ERUDA = ENABLE_ERUDA  # 控制移动端调试工具
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = SQLALCHEMY_TRACK_MODIFICATIONS
    
    # 安全配置
    SECRET_KEY = SECRET_KEY
    
    # 文件上传配置
    UPLOAD_FOLDER = UPLOAD_FOLDER
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
    ALLOWED_IMAGE_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS
    # 添加上传超时设置
    UPLOAD_TIMEOUT = 300  # 5分钟超时
    # 临时文件目录
    UPLOAD_TMP_DIR = '/tmp'

    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # 管理密码
    ADMIN_PASSWORD = ADMIN_PASSWORD

    SITE_NAME = SITE_NAME 