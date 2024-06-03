from flask import *
import pymysql
from pymysql import cursors
from config import BaseConfig
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os
import random
from werkzeug.utils import secure_filename
from markupsafe import Markup  

app = Flask(__name__)
#添加配置文件
app.config.from_object(BaseConfig)
db = SQLAlchemy(app)

secret_key = os.urandom(24)
print(secret_key.hex())
app.secret_key = secret_key.hex()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = 'uploads'  
app.config['COMMENT_UPLOAD_FOLDER'] = 'uploads'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
@app.template_filter('highlight')  
def highlight(text, query):  
    # 实现你的高亮逻辑，这里使用简单的替换作为示例  
    if(text):
      return Markup(text.replace(query, f'<span class="highlight">{query}</span>'))
    return text    

@app.route('/reg', methods = ['GET','POST'])
def register():
   if request.method == 'POST':
        name = request.form["name"]
        pwd1  = request.form["pwd1"]
        pwd2 = request.form["pwd2"]
        if(pwd1 == pwd2):
           password = pwd1
           try:  
             sql = text("INSERT INTO wiki_user(name,password,signature,avatar) VALUES (:name,:password,'nothing to say?','uploads//default.jpg')")
             with app.app_context():  
                with db.engine.connect() as conn: 
                    conn.execute(sql,{'name': name, 'password': password}) 
                    conn.commit()
                    conn.close() 
             return redirect("/user/{}".format(name))
           except Exception as e:  
               db.session.rollback() 
               if 'Username already exists' in str(e):  
                  error_message = 'Username already exists'  
               else:  
                  if 'Password must be at least 6 characters long' in str(e):
                     error_message = 'Password must be at least 6 characters long'  
                  else:
                     error_message = 'An unexpected error occurred while registering'     
               return jsonify({'error': error_message}), 400  
        else:
           return jsonify({'error': 'Different Password'}), 400 
   else:
      return render_template('reg.html')

@app.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
   if request.method == 'POST':
      username = request.form["username"] 
      password = request.form["password"] 
      sql = text("SELECT * FROM wiki_user WHERE name = :name AND password = :password")  
      with app.app_context():  
         with db.engine.connect() as conn:  
            result = conn.execute(sql,{'name': username, 'password': password})  
            row = result.fetchone()  
            if row is not None:  
             session['username'] = username
             session['userid'] = row[0]
             session ['admin'] = row[6]
             return redirect("/user/{}".format(username))
            else:  
             return( "wrong password or user not found")  
   else:
      return render_template('login.html')

@app.route('/user/<username>', methods=['GET', 'POST'])
def userpage(username):
   if 'username' in session:
      if request.method == 'POST':  
        # 处理POST请求（比如保存签名和头像）  
        # 这里只是打印出数据作为示例  
        signature2 = request.form["signature"]  
        avatar2 = request.files["avatar"]
        sql = text("UPDATE wiki_user SET signature = :signature WHERE name = :name")
        if signature2: 
          with app.app_context():  
             with db.engine.connect() as conn: 
                conn.execute(sql,{'signature':signature2,'name': username})
                conn.commit()
                conn.close()
        if avatar2:
            filename = secure_filename(avatar2.filename)
            avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            avatar2.save(avatar_path)
            sql2 = text("UPDATE wiki_user SET avatar = :avatar WHERE name = :name")
            with app.app_context():  
                  with db.engine.connect() as conn: 
                    conn.execute(sql2,{'avatar':avatar_path,'name': username})
                    conn.commit()
                    conn.close()
      sql = text("SELECT * FROM wiki_user WHERE name = :name")
      sql2 = text("SELECT DISTINCT topic_id,topic_name FROM search_view WHERE "  
               "topic_creator = :name")  
      with app.app_context():  
         with db.engine.connect() as conn: 
            user = conn.execute(sql,{'name': username}).fetchone()
            user_wikis = conn.execute(sql2,{'name':username}).fetchall()
            signature = user[3]
            avatar = user[4]
            conn.commit()
            conn.close()
            show_form = False
      if session['username'] == username:
         show_form = True  
      return render_template('user.html',username=username,signature = signature, avatar = avatar,user_wikis=user_wikis,show_form = show_form)
   return redirect('/login')
@app.route('/user/uploads/<filename>')  
def uploaded_file(filename):  
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
 
@app.route('/topic/<topic_id>/uploads/<filename>')  
def uploaded_comment_file(filename,topic_id):  
    return send_from_directory(app.config['COMMENT_UPLOAD_FOLDER'], filename)
 
@app.route('/logout')  
def logout():  
    # 清除session中的用户信息  
    session.pop('username', None)  
    session.pop('userid', None)  
    session.pop('admin', None) 
    # 重定向到登录页面或首页  
    return redirect(url_for('login'))

@app.route('/user/<username>/create_newwiki', methods=['GET', 'POST'])
def creat_newwiki(username):
   if 'username' in session:
     if request.method == 'POST':  
        topic = request.form['topic']
        introduction = request.form['introduction']
        sql_s = sql2 = text("SELECT id FROM wiki_user WHERE name = :username")
        with app.app_context():  
              with db.engine.connect() as conn: 
                 rs=conn.execute(sql_s,{'username':username}).fetchone()
        user_number = rs[0]
        sql = text("INSERT INTO wiki_topic(id,name,creator,createtime,section_number,introduction) VALUES (:id,:topic,:creator,NOW(),0,:introduction)")
        sql2 = text("SELECT * FROM wiki_topic WHERE id = :tid")
        while(True):
           tid = random.randint(1,99999999)
           with app.app_context():  
              with db.engine.connect() as conn: 
                 rs=conn.execute(sql2,{'tid':tid}).fetchone()
                 if rs is None:
                    break
        with app.app_context():  
            with db.engine.connect() as conn: 
               conn.execute(sql,{'id':tid,'topic':topic,'creator':user_number,'introduction':introduction})
               conn.commit()      
        return redirect(url_for('topic_page', topic_id=tid))
     return render_template('create_wiki.html')
   else:
      return redirect('/login') 
 
@app.route('/topic/<int:topic_id>')  
def topic_page(topic_id,methods=['GET', 'POST']):  
    sections = []
    sql1 = text("SELECT name,section_number,introduction,creator FROM wiki_topic WHERE id = :tid") 
    sql2 = text("SELECT * FROM topic_section WHERE topicid = :tid")
    with app.app_context():  
         with db.engine.connect() as conn: 
            rs = conn.execute(sql1,{'tid':topic_id}).fetchone()
            topic = rs[0]
            number = rs[1]
            introduction = rs[2]
            creator_id = rs[3]
            text_result = conn.execute(sql2,{'tid':topic_id}).fetchall()
            for i in range(number):
               rs = text_result[i]
               sections.append(rs)
    show = False
    if 'userid' in session and session['userid'] == creator_id:
       show = True
    if 'admin' in session and session['admin']:
       show = True
    return render_template('topic.html', title=topic, sections=sections,introduction = introduction,topicid = topic_id,show = show)  

@app.route('/topic/<topic_id>/edit_section/<section_id>', methods=['GET', 'POST'])  
def edit_section(topic_id, section_id):  
   if 'username' in session:
      if request.method == 'GET':  
        sql = text("SELECT * FROM topic_section WHERE id = :sid")  
        rs = None
        with app.app_context():  
          with db.engine.connect() as conn: 
            rs = conn.execute(sql,{'sid':section_id}).fetchone()
        title = rs[2]
        content = rs[4]
        return render_template('edit.html', topic_id=topic_id,section_id=section_id,title=title, content=content)  
      if request.method == 'POST':  
       # 处理POST请求，更新部分的内容
        new_title = request.form['new_title']  
        new_content = request.form['new_content']  
        sql = text("CALL UpdateTopicSection(:sid, :newt, :neww)")
        with app.app_context():  
          with db.engine.connect() as conn: 
             conn.execute(sql,{'newt':new_title,'neww':new_content,'sid':section_id})
             conn.commit()
        return redirect(url_for('topic_page', topic_id=topic_id))     # 假设有一个show_section路由  
    # 处理GET请求，显示编辑表单  
   return "无权限",403

@app.route('/wiki/delete/<int:topic_id>', methods=['DELETE'])  
def delete_wiki(topic_id):   
    sql = text("DELETE FROM wiki_topic WHERE id = :tid")
    with app.app_context():  
         with db.engine.connect() as conn: 
            conn.execute(sql,{'tid':topic_id})
            conn.commit()
    return '', 204  # 204 No Content 响应，表示成功但无内容返回


@app.route('/topic/<topic_id>/delete_section/<section_id>', methods=['DELETE'])  
def delete_section(topic_id, section_id):  
   if 'username' in session:
      sql1 = text("DELETE FROM topic_section WHERE id = :sid")
      sql2 = text("UPDATE wiki_topic SET section_number = section_number - 1 WHERE id = :tid")
      with app.app_context():  
         with db.engine.connect() as conn: 
            conn.execute(sql1,{'sid':section_id})
            conn.execute(sql2,{'tid':topic_id})
            conn.commit()
      return jsonify({'message': 'Section deleted successfully'})
   return jsonify({'error': 'Permission denied'}), 403  

@app.route('/topic/<int:topic_id>/add_section', methods=['POST'])  
def add_section(topic_id):  
    # 获取表单数据  
    title = request.form.get('title')  
    content = request.form.get('content')  

    if not title or not content:  
        # 返回错误或重定向到某个页面  
        return 'Error: Both title and content are required.', 400  
    # 构建SQL语句来插入新的章节  
    sql = text("CALL AddTopicSection(:tid, :title, :content)")  
    # 执行SQL语句  
    with app.app_context():  
        with db.engine.connect() as conn:  
             conn.execute(sql, {'tid': topic_id, 'title': title, 'content': content})  
    return redirect(url_for('topic_page', topic_id=topic_id))  
@app.route('/topic/<int:topic_id>/comments', methods=['GET', 'POST'])  
def comments(topic_id):  
    # 从数据库检索特定话题的评论  
   sql = text("SELECT * FROM wiki_revision_with_user WHERE topic_id = :tid ORDER BY re_time")  
   sql2 =text("SELECT name FROM wiki_topic WHERE id = :tid")
   avatar_url = 'default.jpg'  
   with app.app_context():  
     with db.engine.connect() as conn:  
        comments = conn.execute(sql, {'tid': topic_id}).fetchall()  
        name = conn.execute(sql2,{'tid': topic_id}).fetchone()
   if request.method == 'POST':  
        # 从表单中获取评论内容和其他必要信息  
        comment_text = request.form['comment_text']  
        # ... 省略其他表单字段的获取 ...  
        uid = session['userid']
        # 保存评论到数据库  
        sql = text("INSERT INTO wiki_revision(re_time,revisions,userID,star,topic_id) VALUES (now(),:t,:uid,0,:tid)")
        with app.app_context():  
           with db.engine.connect() as conn: 
              conn.execute(sql,{'t':comment_text,'uid':uid,'tid':topic_id})
              conn.commit()
        # 重定向回评论页面以刷新显示  
        return redirect(url_for('comments', topic_id=topic_id))  
   return render_template('comments.html', topic_id=topic_id, name=name,comments=comments,avatar_url = avatar_url) 

@app.route('/search', methods=['GET'])  
def search_form():  
    search_query = request.args.get('q', '', type=str)  
    if search_query:  
        # 如果提供了查询参数，重定向到搜索结果页面  
        return redirect(url_for('search_results', query=search_query))  
    # 如果没有提供查询参数，渲染搜索表单  
    return render_template('search.html', query='')  

@app.route('/search_results/<query>')  
def search_results(query):  
    # 执行搜索查询  
    sql = text("SELECT DISTINCT topic_id,topic_name,topic_introduction FROM search_view WHERE "  
               "topic_name LIKE :query")  
    sql2 = text("SELECT * FROM search_view WHERE "
               "topic_introduction LIKE :query OR "    
               "section_title LIKE :query OR "  
               "section_content LIKE :query OR "
               "topic_creator LIKE :query") 
    with app.app_context():  
        with db.engine.connect() as conn: 
           rs = conn.execute(sql, {"query": f"%{query}%"}).fetchall()
           rs_2 = conn.execute(sql2, {"query": f"%{query}%"}).fetchall()  
    results_t = []
    results = []
    for i in range(len(rs)):
       results_t.append(rs[i])
    for i in range(len(rs_2)):
       results.append(rs_2[i])
    # 将结果传递给模板进行渲染  
    has_results = bool(results_t) or bool(results)  
    return render_template('search_results.html',  has_results=has_results,results_t=results_t, results=results, query=query) 

if __name__ == '__main__':
	app.run()
