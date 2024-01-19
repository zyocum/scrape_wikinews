# scrape_wikinews

Python script for scraping Wikinews articles.

## Setup

Create a Python virtual environment and install the dependencies:

```zsh
# create a virtual environment
$ python3 -m venv scrape_wikinews
# activate the virtual environment
$ source scrape_wikinews/bin/activate
# install dependencies
(scrape_wikinews) $ pip3 install -r requirements.txt
...
```

## Usage

```zsh
$ ./scrape_wikinews.py --help
usage: scrape_wikinews.py [-h] --category CATEGORY
                          [--log-level {notset,debug,info,warning,error,critical}]
                          [--log-file LOG_FILE]

Given a Wikinews category page URL, scrape all news articles from that
categroy as JSON lines. JSON lines (.jsonl) are written to stdout, and a log
of the accessed pages is written to stderr. To run, you might redirect stdout
to a .jsonl file and stderr to a .log file such as the following: # scrape all
published articles (this will take a while) $ ./scrape_wikinews.py --log-
file=en-wikinews-published.log --category=Published > en-wikinews-
published.jsonl # scrape only the Health category $ ./scrape_wikinews.py
--log-file=en-wikinews-health.log --category=Health > en-wikinews-health.jsonl

options:
  -h, --help            show this help message and exit
  --category CATEGORY   en.wikinews category (e.g., "Health" or "Published",
                        see also:
                        https://en.wikinews.org/wiki/Special:Categories)
                        (default: None)
  --log-level {notset,debug,info,warning,error,critical}
                        logging level (default: info)
  --log-file LOG_FILE   path where logging messages will be written (default:
                        None)
```

## Run

To run, choose a Wikinews category to scrape from.

You can see all categories here: [https://en.wikinews.org/wiki/Special:Categories](https://en.wikinews.org/wiki/Special:Categories)

For example, to scrape all published categories (10K+ article pages):

```zsh
(scrape_wikinews) $ ./scrape_wikinews.py --log-file=en-wikinews-published.log --category=Published > en-wikinews-published.jsonl
```

Or to scrape just the [Health](https://en.wikinews.org/wiki/Category:Health) category:

```zsh
(scrape_wikinews) $ ./scrape_wikinews.py --log-file=en-wikinews-health.log --category=Health > en-wikinews-health.jsonl
```

Since the output is in JSON lines format, you can use [`jq`](https://jqlang.github.io/jq/) and [`datamash`](https://www.gnu.org/software/datamash/) to analyze the scraped data:

```zsh
(scrape_wikinews) $ jq '.text|length' en-wikinews.jsonl | datamash --header-out {min,max,mean,pstdev}\ 1 | column -t
min(field-1)  max(field-1)  mean(field-1)    pstdev(field-1)
1             126956        2108.0609889609  3103.367482477
(scrape_wikinews) $ jq -r '.metadata.wikinews_categories[]|match(".*Category:(?<category>.*)")|.captures[].string' en-wikinews.jsonl.bz2 | sort | uniq -c | sort -nr | head | column -t
21921  Published
19676  Archived
7755   Politics_and_conflicts
7449   United_States
6959   North_America
5556   Europe
4471   Crime_and_law
3655   Asia
2828   United_Kingdom
2773   Disasters_and_accidents
```

## Issues

* This only supports English Wikinews (https://en.wikinews.org) for now.
* There may be some issues with cleanly extracting article body texts or metadata in some cases.
