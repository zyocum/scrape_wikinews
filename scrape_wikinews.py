#!/usr/bin/env python3

"""Given a Wikinews category page URL, scrape all news articles from that categroy as JSON lines.
JSON lines (.jsonl) are written to stdout, and a log of the accessed pages is written to stderr.

To run, you might redirect stdout to a .jsonl file and stderr to a .log file such as the following:

# scrape all published articles (this will take a while)
$ ./scrape_wikinews.py --log-file=en-wikinews-published.log --category=Published > en-wikinews-published.jsonl

# scrape only the Health category
$ ./scrape_wikinews.py --log-file=en-wikinews-health.log --category=Health > en-wikinews-health.jsonl
"""

import json
import logging
import sys

from datetime import datetime
from urllib.parse import urlparse

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests_html import HTMLSession

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    """Session adapter that automatically retries requests for certain
    HTTP status codes"""
    session = session or HTMLSession()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# create a session that will be reused for all HTTP(S) requests
session = requests_retry_session()

def category_pages(next_page):
    """Generate Wikinews article page URLs from the category page URL.
    
    next_page: A category page URL such as 'https://en.wikinews.org/wiki/Category:Published' or 'https://en.wikinews.org/wiki/Category:Health'"""
    seen = set()
    while next_page:
        page = session.get(next_page)
        log = logging.info if (page.status_code == 200) else logging.warning
        log(
            f'{datetime.utcnow().isoformat()} '
            f'[{page.status_code} {page.reason}] '
            f'category page url: {page.url}'
        )
        for a in page.html.find('[class~="mw-category"] li a'):
            for url in a.absolute_links:
                if url not in seen:
                    seen.add(url)
                    yield url
        next_pages = [a for a in page.html.find('a') if a.text == 'next page']
        if any(next_pages):
            a, *_ = next_pages
            next_page = a.absolute_links.pop()
        else:
            next_page = None

def metadata(article):
    """Return metadata from the given Wikinews article

    article: requests_html.HTMLResponse
    """
    mw_content_text = article.find('[id~="mw-content-text"]', first=True)
    mw_parser_output = article.find('[class~="mw-parser-output"]')
    try:
        title = article.find('[id="firstHeading"]', first=True).full_text.strip()
    except:
        title = None
    try:
        languages = [e.attrs.get('lang') for e in mw_parser_output]
    except:
        languages = []
    try:
        published_date = article.find('[id="publishDate"]', first=True).attrs.get('title')
    except:
        published_date = None
    try: 
        licenses = [l.attrs.get('href') for l in article.find('[rel="license"]')]
    except:
        licenses = []
    
    parsed_url = urlparse(article.url)
    wikinews_categories = set()
    for a in article.find('[id~="mw-normal-catlinks"] > ul > li > a'):
        wikinews_categories |= a.absolute_links
    return {
        'accessed_date': datetime.utcnow().isoformat(),
        'domain': f'{parsed_url.scheme}://{parsed_url.netloc}',
        'languages': sorted(languages),
        'licenses': licenses,
        'published_date': published_date,
        'title': title,
        'url': article.url,
        'wikinews_categories': sorted(wikinews_categories),
    }

def content(article):
    """Generate plain text content from a Wikinews article HTMLResponse
    
    article: requests_html.HTMLResponse
    
    e.g.:
    url = 'https://en.wikinews.org/wiki/British_supermarket_Tesco_wants_to_start_a_film_downloading_service'
    ''.join(content(session.get(url).html)) -> "The world's third largest supermarket chain, Tesco of Britain, ...
    """
    # handle infoboxes specially
    infobox_descendants = set()
    for ib in article.find('div.infobox'):
        for e in ib.element.iterdescendants():
            infobox_descendants.add(e)
    # filter elements within the mediawiki parser output
    for e in article.find(
        '[id~="mw-content-text"] > [class~="mw-parser-output"] > p, dl, [class~="cquote"]'
    ):
        # skip elements based on the following criteria
        if any((
            e.element in infobox_descendants, # skip elements that are children of infoboxes
            any(e.find('[class="published"]')),
        )):
            continue
        # if we hit these, we've reached the end of the article body
        for id_ in (
            'External_link',
            'External_links',
            'References',
            'Related_Stories',
            'Related_news',
            'Related_stories',
            'See_also',
            'Sister_links',
            'Sources',
        ):
            if any(e.find(f'[id="{id_}"]')):
                return
        yield e.full_text.strip() + '\n'
        # add an extra empty line after headlines
        if e.find('[class~="mw-headline"]'):
            yield ''

def article(url):
    """Construct a JSON object from the given Wikinews article URL"""
    article_page = session.get(url)
    log = logging.info if (article_page.status_code == 200) else logging.warning
    log(
        f'{datetime.utcnow().isoformat()} '
        f'[{article_page.status_code} {article_page.reason}] '
        f'article url: {article_page.url}'
    )
    return {
        'metadata': metadata(article_page.html),
        'text': '\n'.join(content(article_page.html)).strip() + '\n',
    }

if __name__ == '__main__':
    import argparse
    from pathlib import Path
    from logging import _levelToName as log_levels
    log_levels = [l.lower() for _, l in sorted(log_levels.items())]
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__
    )
    parser.add_argument(
        '--category',
        required=True,
        help='en.wikinews category (e.g., "Health" or "Published", see also: https://en.wikinews.org/wiki/Special:Categories)',
    )
    parser.add_argument(
        '--log-level',
        default='info',
        choices=log_levels,
        help='logging level',
    )
    parser.add_argument(
        '--log-file',
        default=None,
        type=Path,
        help='path where logging messages will be written',
    )
    args = parser.parse_args()
    log_level = args.log_level.upper()
    if args.log_file is None:
        logging.basicConfig(
            stream=sys.stderr,
            level=log_level,
        )
    else:
        logging.basicConfig(
            filename=args.log_file,
            filemode='w',
            encoding='utf-8',
            level=log_level,
        )
    logging.info(f'begin scraping category: https://en.wikinews.org/wiki/Category:{args.category}')
    for url in category_pages(category_url):
        if 'wikinews.org/wiki/Category:' not in url:
            print(json.dumps(article(url), ensure_ascii=False))
