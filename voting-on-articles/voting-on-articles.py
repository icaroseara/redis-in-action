import time

ONE_WEEK_IN_SECONDS = 7 * (60 * 60 * 24)
VOTE_SCORE = 432
ARTICLES_PER_PAGE = 25

def article_vote(conn, user, article):
    cutoff = time.time() - ONE_WEEK_IN_SECONDS

    # check to see if the article can still be voted on
    if conn.zscore("time:" + article) < cutoff:
        return

    article_id = article.partition(':')[-1]

    # If the user has not voted for this article before, increment the article score and vote count
    if conn.sadd('voted:' + article_id, user):
        conn.zincrby('score:', article, VOTE_SCORE)
        conn.hincrby(article, 'votes', 1)

def post_article(conn, user, title, link):
    # generate a new article id
    article_id = str(conn.incr('article:'))

    voted = 'voted:' + article_id
    # posting user having voted for the article
    conn.sadd(voted, user)
    # set the article voting information to automatically expire in a week
    conn.expire(voted, ONE_WEEK_IN_SECONDS)

    now = time.time()
    article = 'article:' + article_id

    # Create the article hash
    conn.hmset(article, {
        'title': title,
        'link': link,
        'poster': user,
        'time': now,
        'votes': 1,
    })

    conn.zadd('score:', article, now + VOTE_SCORE)
    conn.zadd('time:', article, now)

    return article_id

    def get_articles(conn, page, order='score:'):
        start = (page - 1) * ARTICLES_PER_PAGE
        end = start + ARTICLES_PER_PAGE - 1

        # set up the start and end indexes for fetching the articles
        ids = conn.zrevrange(order, start, end)

        articles = []
        # get the article information from the list of article ids
        for id in ids:
            article_data = conn.hgetall(id)
            article_data['id'] = id
            articles.append(article_data)

        return articles

    def get_group_articles(conn, group, page, order='score:'):
        key = order + group
        # create a key for each group and each sort order
        if not conn.exists(key):
            # actually sort the articles in the group based on score or recency.
            conn.zinterstore(key,
                ['group:' + group, order],
                aggregate='max',
            )
            # tell Redis to automatically expire the ZSET in 60 seconds.
            conn.expire(key, 60)

            return get_articles(conn, page, key)
