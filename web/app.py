"""Local demo server: opaque cookie ID; all game data stays in server memory."""
import secrets
from threading import RLock
from flask import Flask, jsonify, request, session, render_template
from game.engine import GameEngine
from game.puzzles import PUZZLES


def create_app(agent_factory=None):
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(32)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict', MAX_CONTENT_LENGTH=4096)
    games, lock = {}, RLock()

    def game():
        with lock:
            if session.get('game_id') not in games:
                session['game_id'] = secrets.token_urlsafe(24)
                games[session['game_id']] = GameEngine(agent=agent_factory() if agent_factory else None)
            return games[session['game_id']]

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        return response

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/api/state')
    def state():
        g = game()
        with g.lock:
            return jsonify(g.view())

    @app.get('/api/puzzles')
    def puzzles():
        return jsonify([dict(id=p['id'],title=p['title'],size=p['size']) for p in PUZZLES.values()])

    @app.post('/api/<action>')
    def action(action):
        # Same-origin browser requests and test/CLI JSON clients only.
        if request.headers.get('Sec-Fetch-Site') == 'cross-site':
            return jsonify(code='INVALID_REQUEST'),403
        data = request.get_json(silent=True)
        if not isinstance(data,dict):
            return jsonify(code='INVALID_REQUEST'),400
        g = game()
        with g.lock:
            if action == 'load':
                puzzle_id = data.get('puzzle_id')
                if not isinstance(puzzle_id,str) or puzzle_id not in PUZZLES:
                    return jsonify(code='INVALID_REQUEST'),400
                g.load(puzzle_id)
                result = dict(code='LOADED',message='Hồ sơ mới đã mở.')
            elif action == 'restart':
                g.load(g.puzzle['id'])
                result = dict(code='RESTARTED',message='Phiên tòa bắt đầu lại.')
            elif action == 'verdict':
                if not all(isinstance(data.get(k),str) for k in ('cell','status')):
                    return jsonify(code='INVALID_REQUEST'),400
                result = g.verdict(data['cell'],data['status'])
            elif action == 'hint':
                result = g.hint()
            elif action == 'auto-step':
                result = g.auto_step()
            else:
                return jsonify(code='INVALID_REQUEST'),404
            return jsonify(result | {'state':g.view()})

    return app


app = create_app()
if __name__ == '__main__':
    app.run(host='127.0.0.1',port=5000,debug=False)
