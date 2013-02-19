from celery import Celery
import iron_celery
import feedparser

celery = Celery('tasks', broker='ironmq://', backend='ironcache://')

@celery.task
def getFeed(url):
    print "Got feed "+url
    resp = feedparser.parse(url)
    if not resp.bozo or resp.bozo_exception == feedparser.CharacterEncodingUnknown:
        return resp
    else:
        return {"exception": str(resp.bozo_exception)}
