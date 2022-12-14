from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("blog", __name__)


@bp.route("/")
def index():
    """Show all the posts, most recent first."""
    db = get_db()
    posts = db.execute(
        "SELECT p.id, title, body, created, author_id, username,"
        "(SELECT COUNT(user_id) FROM likes WHERE post_id = p.id) AS likes,"
        "(SELECT COUNT(user_id) FROM comments WHERE post_id = p.id) AS comments"
        " FROM post p JOIN user u ON p.author_id = u.id"
        " ORDER BY created DESC"
    ).fetchall()
    return render_template("blog/index.html", posts=posts)

@bp.route("/comments/<int:post_id>/<action>",methods=("GET", "POST"))
def comments(post_id,action):
    db = get_db()
    post = db.execute(
        "SELECT p.id, title, body, created, author_id, username,"
        "(SELECT COUNT(user_id) FROM likes WHERE post_id = p.id) AS likes,"
        "(SELECT COUNT(user_id) FROM comments WHERE post_id = p.id) AS comments"
        " FROM post p JOIN user u ON p.author_id = u.id"
        " WHERE p.id = ?"
        " ORDER BY created DESC"
        , (post_id,),
    ).fetchone()
    comms = db.execute(
        "SELECT c.id, body, created, user_id, username"
        " FROM comments c JOIN user u ON c.user_id = u.id"
        " WHERE c.post_id = ?"
        " ORDER BY created DESC"
        , (post_id,),
    ).fetchall()

    if request.method == "POST":
        body = request.form["body"]
        error = None

        if not body:
            error = "Body is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO comments(post_id,user_id,body) VALUES(?,?,?)", (post_id,g.user["id"],body)
            )
            db.commit()
            return redirect(url_for('blog.comments', post_id=post_id,action='view'))
    return render_template("blog/comments.html",post=post,comms=comms,action=action)

@bp.route('/delete/<int:comment_id>/<action>')
@login_required
def comment_action(comment_id, action):
    if action == 'delete':
        db = get_db()
        db.execute(
            "DELETE FROM comments WHERE id = ?", (comment_id,)
        )
        db.commit()
    return redirect(request.referrer)

@bp.route('/like/<int:post_id>/<action>')
@login_required
def like_action(post_id, action):
    if action == 'like':
        db = get_db()
        db.execute(
            "INSERT INTO likes(post_id,user_id) VALUES(?,?)", (post_id,g.user["id"])
        )
        db.commit()
    elif action == 'unlike':
        db = get_db()
        db.execute(
            "DELETE FROM likes WHERE post_id = ? AND user_id = ?", (post_id, g.user["id"])
        )
        db.commit()
    return redirect(request.referrer)

def get_post(id, check_author=True):
    """Get a post and its author by id.

    Checks that the id exists and optionally that the current user is
    the author.

    :param id: id of post to get
    :param check_author: require the current user to be the author
    :return: the post with author information
    :raise 404: if a post with the given id doesn't exist
    :raise 403: if the current user isn't the author
    """
    post = (
        get_db()
        .execute(
            "SELECT p.id, title, body, created, author_id, username"
            " FROM post p JOIN user u ON p.author_id = u.id"
            " WHERE p.id = ?",
            (id,),
        )
        .fetchone()
    )

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post["author_id"] != g.user["id"]:
        abort(403)

    return post


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new post for the current user."""
    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO post (title, body, author_id) VALUES (?, ?, ?)",
                (title, body, g.user["id"]),
            )
            db.commit()
            return redirect(url_for("blog.index"))

    return render_template("blog/create.html")


@bp.route("/<int:userid>/profile")
@login_required
def profile(userid):
    """Show all the posts, most recent first."""
    db = get_db()
    posts = db.execute(
        "SELECT p.id, title, body, created, author_id, username,"
        "(SELECT COUNT(user_id) FROM likes WHERE post_id = p.id) AS likes,"
        "(SELECT COUNT(user_id) FROM comments WHERE post_id = p.id) AS comments"
        " FROM post p JOIN user u ON p.author_id = u.id"
        " WHERE p.author_id = ?"
        " ORDER BY created DESC"
        ,(userid,),
    ).fetchall()
    return render_template("blog/profile.html", posts=posts, length=len(posts))


@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    """Update a post if the current user is the author."""
    post = get_post(id)

    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        error = None

        if not title:
            error = "Title is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE post SET title = ?, body = ? WHERE id = ?", (title, body, id)
            )
            db.commit()
            return redirect(url_for("blog.index"))

    return render_template("blog/update.html", post=post)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    """Delete a post.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    get_post(id)
    db = get_db()
    db.execute("DELETE FROM post WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("blog.index"))
