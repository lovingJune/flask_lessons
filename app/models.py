# !/usr/local/bin python3
# coding: utf-8
# @FileName  :models.py
# @Time      :2022-09-12 21:24
# @Author    :Sam

from app import db, app
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5
from time import time
import jwt
import config

# 关注者关联表
followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    followed = db.relationship(
        'User',
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        # return '<User %s>' % self.username
        return '<User {}, Email {}, Password_Hash {}, Posts {}'.format(self.username, self.email, self.password_hash,
                                                                       self.posts)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        # 当前用户所关注的用户帖子列表
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
            followers.c.follower_id == self.id)
        # 当前用户帖子列表
        own = Post.query.filter_by(user_id=self.id)

        return followed.union(own).order_by(
            Post.timestamp.desc())

    # 生成JWT令牌
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode({
            'reset_password': self.id, 'exp': time() + expires_in}, config.Config.SECRET_KEY, algorithm='HS256')


    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, config.Config.SECRET_KEY, algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # 记录帖子的语言。例如中文、英文
    language = db.Column(db.String(5))

    def __repr__(self):
        return '<Post {}>'.format(self.body)


# 使用@login.user_loader装饰器向Flask-Login注册用户加载函数，加载给定ID的用户
@login.user_loader
def load_user(id):
    return User.query.get(int(id))
