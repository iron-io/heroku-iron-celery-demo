# Getting Started With Celery

[Celery](http://www.celeryproject.org) is a task queue for Python. Originally developed as part of the [Django framework](http://www.djangoproject.org), it was split off into its own project and has quickly become the standard for task processing in Python.

This tutorial will show you how to develop a sample application that uses Celery running in a worker dyno. Celery allows for many workers to be processing your task queue, so scaling beyond a single dyno is as simple as adding another dyno.

We'll be using [IronMQ](https://addons.heroku.com/iron_mq) as our "broker" (the message queue Celery stores tasks on) and [IronCache](https://addons.heroku.com/iron_cache) as the "backend" (the datastore Celery stores task state in). These services are hosted, so we don't need to worry about scaling or managing our queue and datastore, and Iron.io wrote a [wrapper library](http://www.iron.io/celery), so they work natively with Celery.

## Getting Set Up

### Adding Addons

The first thing we'll need to do is add IronMQ and IronCache to our application. You can find detailed instructions for each service ([IronMQ](http://devcenter.heroku.com/articles/iron_mq), [IronCache](http://devcenter.heroku.com/articles/iron_cache)), but to summarise, just run the following commands:

	$ heroku addons:add iron_mq:developer
	Adding iron_mq:developer on iron-celery-demo... done, v9 (free)
	Use `heroku addons:docs iron_mq:developer` to view documentation.
	$ heroku addons:add iron_cache:developer
	Adding iron_cache:developer on iron-celery-demo... done, v11 (free)
	Use `heroku addons:docs iron_cache:developer` to view documentation.

This will install the "developer" levels of the addons for your application. This level is the free level, and is appropriate for trying the services out, but you'll want to upgrade to a paid plan before using the services in production.

### Installing Virtualenv

We're going to use [virtualenv](http://pypi.python.org/pypi/virtualenv) to manage our Python environment. You can install virtualenv using pip:

	$ pip install virtualenv

Once installed, create a new environment for the project inside the project folder:

	$ virtualenv venv

This will create a `venv` directory inside the project folder. Run the following command to enter your new environment:

	$ source venv/bin/activate

Now you'll be using a virtual Python installation, unique to your project. This will help manage dependencies. It's important that the above line is run every time you start a new terminal session, to start using the special environment, or things will not work.

### Installing Flask

[Flask](http://flask.pocoo.org) is a microframework for Python. We're going to use it for our web interface, mainly because it's lightweight and will get out of the way of the rest of our code. You can use anything you want, but we wanted to focus on Celery, so we used something with a minimal syntax that functions more-or-less like normal Python code.

You can install flask from pip:

	$ pip install flask

Flask will now be installed into your virtual environment, for your application to use.

### Installing Celery

[Celery](http://www.celeryproject.org) is extremely easy to install, for all the power it brings. You can use pip:

	$ pip install celery

We're also going to want the [Iron.io Celery library](http://www.iron.io/celery), so install that as well:

	$ pip install iron-celery

### Installing Feedparser

[Feedparser](http://code.google.com/p/feedparser) is a Python library that parses RSS feeds. We're going to be writing an application that will download an RSS feed, parse it, and display the items in it in a web interface. We'll be using feedparser to do the bulk of that work. The task can be anything, really; we're just using it to demonstrate the usefulness of Celery.

To get feedparser, use pip:

	$ pip install feedparser

## Writing Our Task

Writing a Celery task is as simple as writing a decorated Python function. Create a file named `tasks.py`, and put the following in it:

	:::python
	from celery import Celery
	import iron_celery
	import feedparser

	celery = Celery('tasks', broker='ironmq://', backend='ironcache://')

	@celery.task
	def getFeed(url):
	    resp = feedparser.parse(url)
    	if not resp.bozo or isinstance(resp.bozo_exception, feedparser.NonXMLContentType):
	        return resp
    	else:
        	return {"exception": str(resp.bozo_exception)}

The above code simply creates an instance of the task queue using the IronMQ and IronCache backends (that's the `celery = Celery()` line) and tells it to [automatically inherit the credentials and project ID](http://dev.iron.io/mq/reference/configuration) for IronMQ and IronCache. Because Heroku will include these credentials in environment variables in production, you don't need them in the code here. For our development environment, however, we need to set those variables; see the [IronMQ](http://devcenter.heroku.com/articles/iron_mq) and [IronCache](http://devcenter.heroku.com/articles/iron_cache) documentation for instructions on how to do that.

Once we get the Celery task queue instantiated in our code, we create a `getFeed(url)` function that's decorated with the `celery.task` decoration. That's all it takes to create a task in Celery.

After that, our code uses feedparser to fetch and parse the passed URL. If it's successful, the response is returned. If there's an error, we return a dict containing a string representation of the error.

## Testing the Task Locally

Now that the task is written, let's test it from our command line. First, you need to start Celery running:

	$ celery -A tasks worker --loglevel=info -E

Now open a new terminal session (remembering to enter the virtual environment) and enter the Python console:

	$ python
	Python 2.7.2 (default, Jun 20 2012, 16:23:33) 
	[GCC 4.2.1 Compatible Apple Clang 4.0 (tags/Apple/clang-418.0.60)] on darwin
	Type "help", "copyright", "credits" or "license" for more information.
	>>> import tasks
	>>> resp = tasks.getFeed.delay("http://blog.iron.io/feeds/posts/default")
	>>> resp.ready()
	False
	>>> resp.ready()
	True
	>>> resp.get()
	{'feed': {'updated': u'2013-02-12T20:54:23.707-08:00', u'gd_image':….

Now that you've verified your task works as expected, let's create a web interface for it.

## Creating a Web Interface

Creating a web interface using Flask is fairly trivial. We're going to use [Twitter's Bootstrap](http://twitter.github.com/bootstrap) for our interface, but the only part that really matters is that a POST request get sent to `/queue` with a `url` field set to the URL that should be downloaded.

First, you're going to create some templates. You can find these in our [Github repo for this tutorial](https://github.com/paddyforan/heroku-iron-celery-demo/tree/master/templates). We need one page to display the results of our task, one page that displays while the task is processing, and one page that users can enter a URL on to start a task.

Our templates use some static files, as well. [You can find those in our Github repo, too.](https://github.com/paddyforan/heroku-iron-celery-demo/tree/master/static)

Finally, we need to write the app to display these pages and queue tasks. Create a file called `app.py` and put the following in it:

    :::python
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

All this app is doing is defining three URLs:

* `/`, the index, simply renders the `index.html` templates.
* `/queue` queues a task using the passed URL in response to a POST request
* `/feed/{id}` displays the result of a task based on the passed ID.

The `/queue` function will queue the task, obtain the task's ID, then redirect the user to the result page for that ID. Because tasks are processed in the background, the task may not be ready for the user yet.

To account for this, the `/feed/{id}` page checks a task's status. If the task is completed, it displays the result. If the task failed due to an error, it displays a traceback. Otherwise, the task is still processing, and the user is instructed to refresh their browser.

That's all it takes to get task processing in the background using Celery.

## Deploying to Heroku

Now that we've built our app and are ready to test it, we need to create a Procfile. This is pretty simple:

	web: python app.py
	celeryd: celery -A tasks worker --loglevel=info -E

We have one web dyno and one Celery dyno.

Now to test our app, we can run foreman:

	$ foreman start
	21:59:31 celeryd.1 | started with pid 3256
	21:59:31 web.1     | started with pid 3255
	21:59:31 web.1     |  * Running on http://0.0.0.0:5000/
	21:59:31 celeryd.1 | [2013-02-15 21:59:31,778: WARNING/MainProcess] celery@slightly.local ready.
	21:59:31 celeryd.1 | [2013-02-15 21:59:31,780: INFO/MainProcess] consumer: 	Connected to ironmq://localhost//.
	
Now if you visit [http://localhost:5000](http://localhost:5000), you should see your index page. Enter a URL and submit it, and you'll see a message that the task hasn't completed. Refresh the page a few times, and you'll see the details of the feed.

Now you can freeze your dependencies with pip to create a requirements file:

	$ pip freeze > requirements.txt

Finally, set up your .gitignore:

	venv
	*.pyc
	.DS_Store
	iron.json

Create your new Heroku app:

	$ heroku create
	Creating stark-window-524... done, stack is cedar
	http://stark-window-524.herokuapp.com/ | git@heroku.com:stark-window-524.git
	Git remote heroku added

Commit and deploy your changes:

	$ git add .
	$ git commit -m "First deploy"
	$ git push heroku master
	Counting objects: 10, done.
	Delta compression using up to 8 threads.
	Compressing objects: 100% (8/8), done.
	Writing objects: 100% (10/10), 3.59 KiB, done.
	Total 10 (delta 0), reused 0 (delta 0)

	-----> Heroku receiving push
	-----> Python app detected
	-----> No runtime.txt provided; assuming python-2.7.3.
	-----> Preparing Python runtime (python-2.7.3)
	-----> Installing Distribute (0.6.34)
	-----> Installing Pip (1.2.1)
	-----> Installing dependencies using Pip (1.2.1)
    	   ...

Finally, you need to spin up a dyno to run your Celery tasks on:

	$ heroku ps:scale celeryd=1
	Scaling celeryd processes… done, now running 1

If you visit your Heroku app, you should see your fully-functioning app running. You're now running Celery tasks on Heroku.
