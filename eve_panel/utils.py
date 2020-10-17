from collections import defaultdict

def sort_by_url(domain):
    sub_urls = {}
    sub_resources = {}

    for url, resource_def in domain.items():
        sub_url, _, rest = url.partition("/")
        if rest:
            sub_urls[rest] = resource_def
        else:
            sub_resources[url] = resource_def
