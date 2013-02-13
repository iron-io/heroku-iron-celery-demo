from celery import Celery
import iron_celery
import feedparser

celery = Celery('tasks', broker='ironmq://', backend='ironcache://')

@celery.task
def add(x, y):
    return x+y

@celery.task
def fib(max):
    curNum = 0
    nextNum = 1
    results = []
    while curNum <= max:
        results.append(curNum)
        newNext = curNum + nextNum
        curNum = nextNum
        nextNum = newNext
    return results

@celery.task
def getFeed(url):
    return feedparser.parse(url)
