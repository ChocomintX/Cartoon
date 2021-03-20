# encoding: utf-8
from flask import Flask, request
from flask_cors import CORS
import datetime
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired, BadSignature
import mangaUtils
import json

app = Flask(__name__)
# 允许跨域请求
CORS(app)

ERROR_CODE = -1
SUCCESS_CODE = 1

# 密钥
SECRET_KEY = 'Chocomint'
# 创建对象的基类:
Base = declarative_base()
# 初始化数据库连接:
engine = create_engine('mysql+mysqlconnector://root:root@localhost:3306/Cartoon')
# 创建DBSession类型:
DBSession = sessionmaker(bind=engine)


# 生成token, 有效时间为600min
def generate_auth_token(userid, expiration=86400):
    # 第一个参数是内部私钥
    # 第二个参数是有效期（秒）
    s = Serializer(SECRET_KEY, expires_in=expiration)
    return s.dumps({'id': userid}).decode()


# token验证函数
def verify_auth_token(id, token):
    s = Serializer(SECRET_KEY)
    results = {}
    try:
        data = s.loads(token)
        if data['id'] == id:
            results['code'] = SUCCESS_CODE
            results['token'] = generate_auth_token(id)
    except SignatureExpired:
        results['code'] = ERROR_CODE
        results['message'] = 'token超时'  # 超时token
    except BadSignature:
        results['code'] = ERROR_CODE
        results['message'] = '非法token'  # 非法token
    return results


# 定义User对象:
class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(255))
    password = Column(String(255))
    name = Column(String(255))


class History(Base):
    __tablename__ = 'history'

    userid = Column(Integer, primary_key=True)
    bookid = Column(String(100), primary_key=True)
    chapterid = Column(String(255))
    bookimg = Column(String(255))
    chaptername = Column(String(255))
    bookname = Column(String(255))
    islike = Column(Integer)
    lastreadtime = Column(DateTime)

    def to_json(self):
        return {
            'userid': self.userid,
            'bookid': self.bookid,
            'chapterid': self.chapterid,
            'bookimg': self.bookimg,
            'chaptername': self.chaptername,
            'bookname': self.bookname,
            'islike': self.islike,
            'lastreadtime': self.lastreadtime.strftime("%m-%d %H:%M:%S")
        }


@app.route('/')
def hello_world():
    return 'hello!'


@app.route('/login', methods=['GET', 'POST'])
def login():
    results = {}
    data = request.get_json()
    username = data['username']
    password = data['password']

    session = DBSession()
    user = session.query(User).filter(User.username == username).first()
    if user is not None and user.password == password:
        results['code'] = SUCCESS_CODE
        results['id'] = user.id
        results['token'] = generate_auth_token(user.id)
    else:
        results['code'] = ERROR_CODE
    session.close()

    return json.dumps(results)


@app.route('/register', methods=['GET', 'POST'])
def register():
    results = {}
    data = request.get_json()
    username = data['username']
    password = data['password']
    name = data['name']

    session = DBSession()
    user = session.query(User).filter(User.username == username).first()

    if user is not None:
        results['code'] = ERROR_CODE
        results['message'] = '用户名已存在！'
    else:
        user = User(username=username,name=name, password=password)
        session.add(user)
        session.commit()
        results['code'] = SUCCESS_CODE
        results['message'] = '账户注册成功！你是第{0}名用户'.format(user.id)
    session.close()
    return results


@app.route('/search', methods=['GET', 'POST'])
def search():
    data = request.get_json()
    results = {}
    try:
        id = int(data['id'])
        token = data['token']
        results.update(verify_auth_token(id, token))

        search_text = data['search_text']
        page = data['page']
        results['results'] = mangaUtils.get_searchList(search_text, page)
    except:
        results['code'] = ERROR_CODE

    return json.dumps(results)


@app.route('/info', methods=['GET', 'POST'])
def info():
    data = request.get_json()
    results = {}
    try:
        id = int(data['id'])
        token = data['token']
        results.update(verify_auth_token(id, token))

        if results['code'] == SUCCESS_CODE:
            bookID = data['bookID']
            session = DBSession()
            history = session.query(History).filter(History.userid == id, History.bookid == bookID).first()
            if history is not None:
                results['isLike'] = history.islike
                results['chapterid'] = history.chapterid
                results['chaptername'] = history.chaptername
            else:
                results['isLike'] = 0
                results['chapterid'] = ''
                results['chaptername'] = ''
            session.close()

            results.update(mangaUtils.get_bookInfo(bookID))
    except Exception as e:
        results['code'] = ERROR_CODE
        results['message'] = str(e)

    return json.dumps(results)


@app.route('/show', methods=['GET', 'POST'])
def show():
    data = request.get_json()
    results = {}

    try:
        id = int(data['id'])
        token = data['token']
        results.update(verify_auth_token(id, token))

        if results['code'] == SUCCESS_CODE:
            session = DBSession()
            bookid = data['bookID']
            chapterid = data['chapterID']
            index = data['index']
            chaptername = data['chapterName']
            history = session.query(History).filter(History.userid == id, History.bookid == bookid + 'bz').first()
            if history is not None:
                history.chapterid = index
                history.lastreadtime = datetime.datetime.now()
                history.chaptername = chaptername
            else:
                history = History(userid=data['id'],
                                  bookid=bookid + 'bz',
                                  bookname=data['bookName'],
                                  bookimg=data['bookImg'],
                                  chaptername=chaptername,
                                  chapterid=index,
                                  islike=0,
                                  lastreadtime=datetime.datetime.now())
                session.add(history)
            session.commit()
            session.close()
            results.update(mangaUtils.get_chapterImages(bookid, chapterid))
    except Exception as e:
        results['code'] = ERROR_CODE
        results['message'] = str(e)

    return json.dumps(results)


@app.route('/like', methods=['GET', 'POST'])
def like():
    data = request.get_json()
    results = {}

    try:
        id = int(data['id'])
        token = data['token']
        results.update(verify_auth_token(id, token))

        if results['code'] == SUCCESS_CODE:
            session = DBSession()
            bookid = data['bookid']
            history = session.query(History).filter(History.userid == id, History.bookid == bookid).first()
            if history is not None:
                isLike = history.islike
                if isLike == 1:
                    history.islike = 0
                else:
                    history.islike = 1
                session.commit()
                results['isLike'] = history.islike
            else:
                history = History(userid=data['id'],
                                  bookid=data['bookid'],
                                  bookname=data['bookname'],
                                  bookimg=data['bookimg'],
                                  chaptername=data['chaptername'],
                                  chapterid=data['chapterid'],
                                  islike=1,
                                  lastreadtime=datetime.datetime.now())
                session.add(history)
                session.commit()
            session.close()
    except Exception as e:
        results['code'] = ERROR_CODE
        results['message'] = str(e)

    return json.dumps(results)


@app.route('/gethistory', methods=['GET', 'POST'])
def gethistory():
    data = request.get_json()
    results = {}

    try:
        id = int(data['id'])
        token = data['token']
        results.update(verify_auth_token(id, token))

        if results['code'] == SUCCESS_CODE:
            session = DBSession()
            historys = []
            if data['mode'] == 'like':
                historys = list(item.to_json() for item in
                                session.query(History).filter(History.userid == id, History.islike == 1).all())
            elif data['mode'] == 'history':
                historys = list(item.to_json() for item in
                                session.query(History).order_by(History.lastreadtime.desc()).filter(
                                    History.userid == id).all())

            results['historys'] = historys
            session.close()
    except Exception as e:
        results['code'] = ERROR_CODE
        results['message'] = str(e)

    return json.dumps(results)


@app.route('/deletelike', methods=['GET', 'POST'])
def deletelike():
    data = request.get_json()
    results = {}

    try:
        id = int(data['id'])
        token = data['token']
        results.update(verify_auth_token(id, token))

        if results['code'] == SUCCESS_CODE:
            session = DBSession()
            deleteList = data['list']
            for item in deleteList:
                print(item)
                history = session.query(History).filter(History.userid == id, History.bookid == item['bookid']).first()
                history.islike = 0

            historys = list(
                i.to_json() for i in session.query(History).filter(History.userid == id, History.islike == 1).all())
            results['likes'] = historys
            session.commit()
            session.close()
    except Exception as e:
        results['code'] = ERROR_CODE
        results['message'] = str(e)

    return json.dumps(results)


if __name__ == '__main__':
    app.run()
