import os
from celery.result import AsyncResult
from flask import Flask
from flask import redirect
from flask import request
from flask import render_template
from tasks import getFeed
from iron_celery import iron_cache_backend

app = Flask(__name__)
backend = iron_cache_backend.IronCacheBackend("ironcache://")

@app.route('/')
def hello():
    return render_template('index.html')

@app.route('/queue', methods=['POST'])
def runTask():
    res = getFeed.delay(request.form['url'])
    return redirect('/feed/'+res.id)

@app.route('/feed/<id>')
def show_feed(id):
    result = AsyncResult(id, backend=backend)
    if result.ready():
        return render_template('feed.html', feed=result.get())
    elif result.failed():
        return result.traceback
    else:
        return render_template('processing.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
