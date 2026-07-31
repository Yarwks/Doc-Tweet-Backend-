from flask import Blueprint, request, jsonify
from app import db
from app.models import Post, Question

posts_bp = Blueprint('posts', __name__)


@posts_bp.route('/api/posts', methods=['GET'])
def get_posts():
    filter_type = request.args.get('type')

    
    if filter_type == 'post':
        posts = Post.query.order_by(Post.created_at.desc()).all()
        result = []
        for p in posts:
            result.append({
                "id": p.id,
                "title": p.title,
                "content": p.content,
                "author_name": p.author,
                "type": "post",
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else ""
            })
        return jsonify(result), 200

    
    elif filter_type == 'question_blog':
        questions = Question.query.order_by(Question.created_at.desc()).all()
        result = []
        for q in questions:
            result.append({
                "id": q.id,
                "title": q.title,
                "content": q.content,
                "author_name": q.author,
                "is_anonymous": q.is_anonymous,
                "type": "question",
                "created_at": q.created_at.strftime("%Y-%m-%d %H:%M") if q.created_at else ""
            })
        return jsonify(result), 200

    return jsonify([]), 200



@posts_bp.route('/api/posts', methods=['POST'])
def create_post():
    data = request.get_json() or {}
    post_type = data.get('type', 'post')

    
    if post_type == 'question':
        new_question = Question(
            title=data.get('title', 'Untitled Question'),
            content=data.get('content', ''),
            author=data.get('author_name', 'Anonymous User'),
            is_anonymous=data.get('is_anonymous', False)
        )
        db.session.add(new_question)
        db.session.commit()
        return jsonify({"message": "Question published successfully!"}), 201

    
    else:
        new_post = Post(
            title=data.get('title', 'Quick Post'),
            content=data.get('content', ''),
            author=data.get('author_name', 'Anonymous User')
        )
        db.session.add(new_post)
        db.session.commit()
        return jsonify({"message": "Post published successfully!"}), 201