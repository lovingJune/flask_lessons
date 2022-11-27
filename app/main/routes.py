# !/usr/local/bin python3
# coding: utf-8
# @FileName  :routes.py
# @Time      :2022-10-14 23:16
# @Author    :Sam

# 从app包中导入 app这个实例
from app import db
from flask import render_template, flash, redirect, url_for, request, g
from flask_login import current_user
from app.models import User, Post
from flask_login import login_required

from datetime import datetime
from app.main.forms import EmptyForm, PostForm, EditProfileForm
import config
from flask_babel import get_locale
from guess_language import guess_language
from flask import jsonify, g, current_app
from app.translate import translate
from app.main import bp
from app.main.forms import SearchForm
from app.main.forms import MessageForm
from app.models import Message, Notification


# 记录上次访问的时间
@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()
    # g.locale = 'zh' if str(get_locale()).startswith('zh') else str(get_locale())
    g.locale = str(get_locale())


# 2个路由
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index/', methods=['GET', 'POST'])
@login_required
# 1个视图函数
def index():
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.post.data)
        print("language:", language)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('main.index'))
    # 分页获取当前页
    page = request.args.get('page', 1, type=int)
    # 提交博客后，在index页面展示当前用户和关注用户的帖子列表
    posts = current_user.followed_posts().paginate(page, config.Config.POSTS_PER_PAGE, False)
    # 下一页、上一页链接 paginate()对象的has_next、has_prev方法
    next_url = url_for('main.index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) if posts.has_prev else None

    return render_template('index.html', title='Home Page', form=form, posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)

    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page, config.Config.POSTS_PER_PAGE, False)

    # 下一页、上一页链接 paginate()对象的has_next、has_prev方法
    next_url = url_for('main.explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) if posts.has_prev else None

    # 页面 跟主页面非常相似，因此重用了index.html
    # print('='*10,posts,dir(posts))
    return render_template('index.html', title='Explore', posts=posts.items, next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()

    page = request.args.get('page', 1, type=int)

    posts = user.posts.order_by(Post.timestamp.desc()).paginate(page, config.Config.POSTS_PER_PAGE, False)

    next_url = url_for('main.user', username=user.username, page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username, page=posts.prev_num) if posts.has_prev else None

    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items, next_url=next_url, prev_url=prev_url, form=form)


@bp.route('/edit_profile/', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()

        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))

    form.username.data = current_user.username
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)


# 关注
@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('main.user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash('You are following {}!'.format(username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


# 取消关注
@bp.route('/unfollow/<username>', methods=["POST"])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('main.user', username=username))

        current_user.unfollow(user)
        db.session.commit()
        flash('You are not following {}.'.format(username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


# 翻译
@bp.route('/translate/', methods=['POST'])
@login_required
def translate_text():
    return jsonify(
        {'text': translate(request.form['text'], request.form['source_language'], request.form['dest_language'])})


# 搜索

@bp.route('/search/')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))

    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page,
                               config.Config.POSTS_PER_PAGE)

    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None

    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None

    return render_template('search.html', title='Search', posts=posts,
                           next_url=next_url, prev_url=prev_url)


# 用户信息弹窗视图。当鼠标悬停在用户名上在弹窗中显示用户的简要信息
@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    return render_template('user_popup.html', user=user, form=form)


# 发送私有消息
@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash('您的消息已发送 ~')
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title='Send Message',
                           form=form, recipient=recipient)


# 查看私人消息路由
@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    # 当用户进入消息页面时，未读计数回到零
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['POSTS_PER_PAGE'],
        error_out=False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


# 通知视图函数
@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])


# 导出帖子视图函数
@bp.route('/export_posts/')
@login_required
def export_posts():
    if current_user.get_task_in_progress('export_posts'):
        flash('An export task is currently in progress')
    else:
        current_user.launch_task('export_posts', 'Exporting posts...')
        db.session.commit()
    return redirect(url_for('main.user', username=current_user.username))
