from celery import Celery
import iron_celery
import feedparser

celery = Celery('tasks', broker='ironmq://', backend='ironcache://')

@celery.task
def getFeed(url):
    print "Got feed "+url
    resp = feedparser.parse(url)
    if not resp.bozo:
        return resp
    else:
        return {"exception": {"message": resp.bozo_exception.getMessage(), "line": resp.bozo_exception.getLineNumber()}}
