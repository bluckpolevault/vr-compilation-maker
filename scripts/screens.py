
import util


def get_rating(filename):
    movie_id = util.get_movie_id(filename)
    db = util.get_db()
    cur = db.execute(
        'select id, rating from thumbnail where movie_id = ? and filename = ?',
        (movie_id, filename.name))
    return cur.fetchone()
