import os
import re
import requests
from bs4 import BeautifulSoup
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from werkzeug.utils import secure_filename
from app import db, login_manager
from app.models import Recipe, Step, Note, Ingredient, CommonIngredient, FinalImage, User
from datetime import datetime
from flask_login import login_user, logout_user, login_required, current_user

main = Blueprint('main', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def debugLog(*args):
    """调试日志函数"""
    current_app.logger.debug(*args)

def debugError(*args):
    """调试错误日志函数"""
    current_app.logger.error(*args)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_IMAGE_EXTENSIONS']

@main.route('/parse_video_url', methods=['POST'])
def parse_video_url():
    url = request.json.get('url')
    if not url:
        return jsonify({'success': False, 'error': '无效的URL'})
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        current_app.logger.info(f'正在解析URL: {url}')
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()  # 检查响应状态
        
        # 尝试不同的编码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 按优先级尝试不同的标题获取方法
        title = None
        
        # 1. 尝试获取 og:title
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title = og_title.get('content')
            current_app.logger.info(f'从og:title获取到标题: {title}')
        
        # 2. 尝试获取 title 标签
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.string
                current_app.logger.info(f'从title标签获取到标题: {title}')
        
        # 3. 尝试获取 h1
        if not title:
            h1_tag = soup.find('h1')
            if h1_tag:
                title = h1_tag.get_text(strip=True)
                current_app.logger.info(f'从h1标签获取到标题: {title}')
        
        # 清理标题
        if title:
            # 移除多余空白字符
            title = ' '.join(title.split())
            # 限制标题长度
            if len(title) > 100:
                title = title[:97] + '...'
        else:
            title = '未能获取标题'
            current_app.logger.warning('未找到标题')
        
        return jsonify({
            'success': True,
            'data': {
                'title': title,
                'url': url
            }
        })
        
    except requests.Timeout:
        current_app.logger.info(f'解析超时: {url}')
        return jsonify({
            'success': True,
            'data': {
                'title': '获取超时',
                'url': url
            }
        })
    except requests.RequestException as e:
        current_app.logger.error(f'请求失败: {url}, 错误: {str(e)}')
        return jsonify({
            'success': True,
            'data': {
                'title': '无法访问链接',
                'url': url
            }
        })
    except Exception as e:
        current_app.logger.error(f'解析失败: {url}, 错误: {str(e)}')
        return jsonify({
            'success': True,
            'data': {
                'title': '解析失败',
                'url': url
            }
        })

@main.route('/')
def index():
    recipes = Recipe.query.order_by(Recipe.created_at.desc()).all()
    debug_config = {
        'ENABLE_ERUDA': current_app.config['ENABLE_ERUDA']
    }
    return render_template('index.html', recipes=recipes, debug_config=debug_config)

@main.route('/recipe/new', methods=['POST'])
@login_required
def new_recipe():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if name:
            recipe = Recipe(name=name, description=description)
            db.session.add(recipe)
            db.session.commit()  # 先提交以获取 recipe_id

            # 处理成品图片
            final_images = request.files.getlist('final_images[]')
            for i, image in enumerate(final_images):
                if image and allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    image_path = os.path.join('uploads', filename)
                    image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    
                    final_image = FinalImage(
                        recipe_id=recipe.id,
                        image_path=image_path,
                        order=i
                    )
                    db.session.add(final_image)

            # 处理食材
            ingredients = request.form.getlist('ingredients[]')
            amounts = request.form.getlist('amounts[]')
            ingredient_notes = request.form.getlist('ingredient_notes[]')
            
            for i in range(len(ingredients)):
                if ingredients[i]:
                    ingredient = Ingredient(
                        recipe_id=recipe.id,
                        name=ingredients[i],
                        amount=amounts[i] if i < len(amounts) else None,
                        note=ingredient_notes[i] if i < len(ingredient_notes) else None
                    )
                    db.session.add(ingredient)

            # 处理步骤
            steps = request.form.getlist('steps[]')
            step_images = request.files.getlist('step_images[]')
            
            for i, description in enumerate(steps, 1):
                if description:
                    image_path = None
                    if i <= len(step_images) and step_images[i-1].filename:
                        image = step_images[i-1]
                        if allowed_file(image.filename):
                            filename = secure_filename(image.filename)
                            image_path = os.path.join('uploads', filename)
                            image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    
                    step = Step(
                        recipe_id=recipe.id,
                        order=i,
                        description=description,
                        image_path=image_path
                    )
                    db.session.add(step)

            # 处理笔记
            notes = request.form.getlist('notes[]')
            for note_content in notes:
                if note_content:
                    note = Note(recipe_id=recipe.id, content=note_content)
                    db.session.add(note)
            
            db.session.commit()
            return jsonify({'success': True, 'recipe_id': recipe.id})
            
    return jsonify({'success': False, 'error': '创建失败'})

@main.route('/recipe/<int:recipe_id>/ingredient/add', methods=['POST'])
@login_required
def add_ingredient(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    name = request.form.get('name')
    amount = request.form.get('amount')
    note = request.form.get('note')
    
    if name:
        ingredient = Ingredient(recipe_id=recipe_id, name=name, amount=amount, note=note)
        db.session.add(ingredient)
        db.session.commit()
        flash('食材添加成功！', 'success')
    
    return redirect(url_for('main.recipe', recipe_id=recipe_id))

@main.route('/recipe/<int:recipe_id>')
def recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # 序列化食材数据
    ingredients_data = [{
        'name': ingredient.name,
        'amount': ingredient.amount or '',
        'note': ingredient.note or ''
    } for ingredient in recipe.ingredients]
    
    # 序列化成品图片数据
    final_images_data = [{
        'id': image.id,
        'path': image.image_path,
        'order': image.order
    } for image in sorted(recipe.final_images, key=lambda x: x.order)]
    
    # 添加调试配置
    debug_config = {
        'ENABLE_ERUDA': current_app.config['ENABLE_ERUDA']
    }
    
    return render_template('recipe.html', 
                         recipe=recipe, 
                         ingredients_json=ingredients_data,
                         final_images_json=final_images_data,
                         debug_config=debug_config)

@main.route('/recipe/<int:recipe_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    
    if request.method == 'GET':
        return jsonify({
            'id': recipe.id,
            'name': recipe.name,
            'description': recipe.description,
            'final_images': [{
                'id': image.id,
                'path': image.image_path,
                'order': image.order
            } for image in sorted(recipe.final_images, key=lambda x: x.order)],
            'ingredients': [{
                'name': i.name,
                'amount': i.amount,
                'note': i.note
            } for i in recipe.ingredients],
            'steps': [{
                'id': s.id,
                'order': s.order,
                'description': s.description,
                'image_path': s.image_path
            } for s in sorted(recipe.steps, key=lambda x: x.order)],
            'notes': [{
                'id': n.id,
                'content': n.content,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M')
            } for n in sorted(recipe.notes, key=lambda x: x.created_at, reverse=True)]
        })
        
    # POST 请求处理
    recipe.name = request.form.get('name')
    recipe.description = request.form.get('description')
    recipe.updated_at = datetime.now()
    
    # 处理成品图片
    final_images = request.files.getlist('final_images[]')
    if final_images:
        for image in final_images:
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join('uploads', filename)
                image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                
                # 获取当前最大的order值
                max_order = db.session.query(db.func.max(FinalImage.order)).filter_by(recipe_id=recipe_id).scalar() or -1
                
                final_image = FinalImage(
                    recipe_id=recipe_id,
                    image_path=image_path,
                    order=max_order + 1
                )
                db.session.add(final_image)
    
    # 更新食材
    for ingredient in recipe.ingredients:
        db.session.delete(ingredient)
    
    ingredients = request.form.getlist('ingredients[]')
    amounts = request.form.getlist('amounts[]')
    ingredient_notes = request.form.getlist('ingredient_notes[]')
    
    for i in range(len(ingredients)):
        if ingredients[i]:
            ingredient = Ingredient(
                recipe_id=recipe.id,
                name=ingredients[i],
                amount=amounts[i] if i < len(amounts) else None,
                note=ingredient_notes[i] if i < len(ingredient_notes) else None
            )
            db.session.add(ingredient)

    # 更新步骤
    for step in recipe.steps:
        db.session.delete(step)
    
    steps = request.form.getlist('steps[]')
    step_images = request.files.getlist('step_images[]')
    
    for i, description in enumerate(steps, 1):
        if description:
            image_path = None
            if i <= len(step_images) and step_images[i-1].filename:
                image = step_images[i-1]
                if allowed_file(image.filename):
                    filename = secure_filename(image.filename)
                    image_path = os.path.join('uploads', filename)
                    image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
            step = Step(
                recipe_id=recipe.id,
                order=i,
                description=description,
                image_path=image_path
            )
            db.session.add(step)

    # 更新笔记
    notes = request.form.getlist('notes[]')
    note_ids = request.form.getlist('note_ids[]')
    
    # 删除未包含在提交表单中的笔记
    for note in recipe.notes:
        if str(note.id) not in note_ids:
            db.session.delete(note)
    
    # 更新或创建笔记
    for i, note_content in enumerate(notes):
        if note_content:
            if i < len(note_ids) and note_ids[i]:  # 更新现有笔记
                note = Note.query.get(note_ids[i])
                if note:
                    # 只有当内容真正改变时才更新时间戳
                    if note.content != note_content:
                        note.content = note_content
                        note.updated_at = datetime.now()
                    else:
                        # 内容未改变，只需保存内容
                        note.content = note_content
            else:  # 创建新笔记
                note = Note(
                    recipe_id=recipe.id,
                    content=note_content,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.session.add(note)
    
    db.session.commit()
    return jsonify({'success': True, 'recipe_id': recipe.id})

@main.route('/recipe/<int:recipe_id>/step/add', methods=['POST'])
@login_required
def add_step(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    description = request.form.get('description')
    order = len(recipe.steps) + 1
    
    image = request.files.get('image')
    image_path = None
    
    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image_path = os.path.join('uploads', filename)
        image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    
    step = Step(recipe_id=recipe_id, description=description, order=order, image_path=image_path)
    db.session.add(step)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'step': {
            'id': step.id,
            'order': step.order,
            'description': step.description,
            'image_path': image_path
        }
    })

@main.route('/recipe/<int:recipe_id>/step/<int:step_id>/edit', methods=['POST'])
@login_required
def edit_step(recipe_id, step_id):
    step = Step.query.get_or_404(step_id)
    description = request.form.get('description')
    
    if description:
        step.description = description
        image = request.files.get('image')
        
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join('uploads', filename)
            image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            step.image_path = image_path
            
        db.session.commit()
        return jsonify({'success': True})
        
    return jsonify({'success': False, 'error': '更新失败'})

@main.route('/recipe/<int:recipe_id>/step/<int:step_id>/delete', methods=['POST'])
@login_required
def delete_step(recipe_id, step_id):
    step = Step.query.get_or_404(step_id)
    db.session.delete(step)
    
    # 重新排序剩余步骤
    remaining_steps = Step.query.filter_by(recipe_id=recipe_id).order_by(Step.order).all()
    for i, step in enumerate(remaining_steps, 1):
        step.order = i
    
    db.session.commit()
    return jsonify({'success': True})

@main.route('/recipe/<int:recipe_id>/note/add', methods=['POST'])
@login_required
def add_note(recipe_id):
    content = request.form.get('content')
    if content:
        note = Note(recipe_id=recipe_id, content=content)
        db.session.add(note)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': '笔记内容不能为空'})

@main.route('/recipe/<int:recipe_id>/delete', methods=['POST'])
@login_required
def delete_recipe(recipe_id):
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        
        # 删除食材
        for ingredient in recipe.ingredients:
            db.session.delete(ingredient)
        
        # 删除步骤
        for step in recipe.steps:
            # 如果步骤有图片，删除图片文件
            if step.image_path:
                image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(step.image_path))
                debugLog('尝试删除步骤图片:', image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    debugLog('已删除步骤图片:', image_path)
            db.session.delete(step)
        
        # 删除笔记
        for note in recipe.notes:
            db.session.delete(note)
        
        # 删除成品图片
        for image in recipe.final_images:
            image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(image.image_path))
            debugLog('尝试删除成品图片:', image_path)
            if os.path.exists(image_path):
                os.remove(image_path)
                debugLog('已删除成品图片:', image_path)
            db.session.delete(image)
        
        # 删除菜谱
        db.session.delete(recipe)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        debugError('删除菜谱失败:', str(e))
        return jsonify({'success': False, 'error': str(e)})

@main.route('/recipe/<int:recipe_id>/delete_image', methods=['POST'])
@login_required
def delete_recipe_image(recipe_id):
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        if recipe.final_image:
            # 删除图片文件
            image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(recipe.final_image))
            debugLog('尝试删除文件:', image_path)
            if os.path.exists(image_path):
                os.remove(image_path)
                debugLog('已删除物理文件:', image_path)
            else:
                debugLog('文件不存在:', image_path)
            
            # 更新数据库
            recipe.final_image = None
            db.session.commit()
            return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@main.route('/common_ingredients', methods=['GET'])
def get_common_ingredients():
    ingredients = CommonIngredient.query.order_by(CommonIngredient.order).all()
    return jsonify([{
        'id': ing.id,
        'name': ing.name,
        'unit': ing.unit,
        'order': ing.order
    } for ing in ingredients])

@main.route('/common_ingredients/reorder', methods=['POST'])
@login_required
def reorder_common_ingredients():
    try:
        new_order = request.json
        for item in new_order:
            ingredient = CommonIngredient.query.get(item['id'])
            if ingredient:
                ingredient.order = item['order']
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@main.route('/common_ingredients/update', methods=['POST'])
@login_required
def update_common_ingredients():
    try:
        items = request.json
        
        # 获取所有现有的常用食材ID
        existing_ids = set(item.id for item in CommonIngredient.query.all())
        updated_ids = set()
        
        for item in items:
            if item.get('id'):  # 更新现有食材
                ingredient = CommonIngredient.query.get(item['id'])
                if ingredient:
                    ingredient.name = item['name']
                    ingredient.unit = item['unit']
                    ingredient.order = item['order']
                    updated_ids.add(item['id'])
            else:  # 添加新食材
                ingredient = CommonIngredient(
                    name=item['name'],
                    unit=item['unit'],
                    order=item['order']
                )
                db.session.add(ingredient)
        
        # 删除未包含在更新列表中的食材
        for id in existing_ids - updated_ids:
            ingredient = CommonIngredient.query.get(id)
            if ingredient:
                db.session.delete(ingredient)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@main.route('/recipe/<int:recipe_id>/final_image/add', methods=['POST'])
@login_required
def add_final_image(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    image = request.files.get('image')
    
    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image_path = os.path.join('uploads', filename)
        image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        
        # 获取当前最大的order值
        max_order = db.session.query(db.func.max(FinalImage.order)).filter_by(recipe_id=recipe_id).scalar() or -1
        
        final_image = FinalImage(
            recipe_id=recipe_id,
            image_path=image_path,
            order=max_order + 1
        )
        db.session.add(final_image)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'image': {
                'id': final_image.id,
                'path': final_image.image_path,
                'order': final_image.order
            }
        })
    
    return jsonify({'success': False, 'error': '上传失败'})

@main.route('/recipe/<int:recipe_id>/final_image/<int:image_id>/delete', methods=['POST'])
@login_required
def delete_final_image(recipe_id, image_id):
    image = FinalImage.query.get_or_404(image_id)
    if image.recipe_id != recipe_id:
        return jsonify({'success': False, 'error': '无权限'})
    
    try:
        # 删除物理文件
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(image.image_path))
        debugLog('尝试删除文件:', image_path)
        if os.path.exists(image_path):
            os.remove(image_path)
            debugLog('已删除物理文件:', image_path)
        else:
            debugLog('文件不存在:', image_path)
        
        # 删除数据库记录
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        debugError('删除图片失败:', str(e))
        return jsonify({'success': False, 'error': str(e)})

@main.route('/recipe/<int:recipe_id>/final_images/reorder', methods=['POST'])
@login_required
def reorder_final_images(recipe_id):
    try:
        new_order = request.json
        for item in new_order:
            image = FinalImage.query.get(item['id'])
            if image and image.recipe_id == recipe_id:
                image.order = item['order']
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('main.index'))
        else:
            flash('用户名或密码错误', 'danger')
    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    password = data.get('password')
    
    # 获取管理员用户
    admin = User.query.filter_by(username='admin').first()
    
    # 如果管理员用户不存在，创建一个
    if not admin:
        admin = User(username='admin')
        admin.set_password(current_app.config['ADMIN_PASSWORD'])
        db.session.add(admin)
        db.session.commit()
    
    # 验证密码
    if admin.check_password(password):
        login_user(admin, remember=True)
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': '密码错误'})

@main.route('/test_login_status')
def test_login_status():
    if current_user.is_authenticated:
        return jsonify({
            'logged_in': True,
            'username': current_user.username
        })
    return jsonify({
        'logged_in': False
    })

@main.route('/admin/change_password', methods=['POST'])
@login_required
def change_admin_password():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': '未登录'})
        
    data = request.get_json()
    new_password = data.get('new_password')
    
    # 修改密码
    current_user.set_password(new_password)
    db.session.commit()
    
    return jsonify({'success': True})

@main.route('/admin/change_site_name', methods=['POST'])
@login_required
def change_site_name():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': '未登录'})
        
    data = request.get_json()
    site_name = data.get('site_name')
    
    if not site_name:
        return jsonify({'success': False, 'error': '站点名称不能为空'})
    
    try:
        # 修改配置文件
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.py')
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则表达式替换 SITE_NAME 的值
        new_content = re.sub(
            r'SITE_NAME\s*=\s*["\'].*["\']',
            f'SITE_NAME = "{site_name}"',
            content
        )
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # 更新当前应用的配置
        current_app.config['SITE_NAME'] = site_name
        
        return jsonify({'success': True})
    except Exception as e:
        debugError('修改站点名称失败:', str(e))
        return jsonify({'success': False, 'error': '修改站点名称失败，请重试'})

@main.route('/admin/change_debug_mode', methods=['POST'])
@login_required
def change_debug_mode():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': '未授权的操作'})
    
    try:
        data = request.get_json()
        enable_eruda = data.get('enable_eruda', False)
        
        # 读取配置文件
        with open('config.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用正则表达式替换 ENABLE_ERUDA 的值
        new_content = re.sub(
            r'ENABLE_ERUDA\s*=\s*(True|False)',
            f'ENABLE_ERUDA = {enable_eruda}',
            content
        )
        
        if new_content == content:
            raise Exception('未找到 ENABLE_ERUDA 配置项或替换失败')
        
        # 写入新的配置
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # 更新当前应用的配置
        current_app.config['ENABLE_ERUDA'] = enable_eruda
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}) 