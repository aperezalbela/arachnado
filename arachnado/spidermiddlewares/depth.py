import logging
from six.moves.urllib.parse import urlparse
from scrapy.http import Request


logger = logging.getLogger(__name__)


class DepthMiddleware(object):

    def __init__(self, maxdepth, stats=None, verbose_stats=False, prio=1, domainsdepth=None):
        self.maxdepth = maxdepth
        self.stats = stats
        self.verbose_stats = verbose_stats
        self.prio = prio
        if domainsdepth:
            self.domainsdepth = domainsdepth
        else:
            self.domainsdepth = {}

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        maxdepth = settings.getint('DEPTH_LIMIT')
        verbose = settings.getbool('DEPTH_STATS_VERBOSE')
        prio = settings.getint('DEPTH_PRIORITY')
        domainsdepth = settings.get('DEPTH_DOMAINS_LIMITS')
        return cls(maxdepth, crawler.stats, verbose, prio, domainsdepth)

    def process_spider_output(self, response, result, spider):
        def _filter(request):
            if isinstance(request, Request):
                depth = response.meta['depth'] + 1
                request.meta['depth'] = depth
                if 'splash' in request.meta:
                    url = request.meta.get("url", None)
                else:
                    url = request.url
                parsed_url = urlparse(url)
                depthlimit = self.domainsdepth.get(parsed_url.netloc, self.maxdepth)
                if self.prio:
                    request.priority -= depth * self.prio
                if self.maxdepth and depth > depthlimit:
                    logger.debug(
                        "Ignoring link (depth > %(maxdepth)d): %(requrl)s ",
                        {'maxdepth': self.maxdepth, 'requrl': request.url},
                        extra={'spider': spider}
                    )
                    return False
                elif self.stats:
                    if self.verbose_stats:
                        self.stats.inc_value('request_depth_count/%s' % depth,
                                             spider=spider)
                    self.stats.max_value('request_depth_max', depth,
                                         spider=spider)
            return True

        # base case (depth=0)
        if self.stats and 'depth' not in response.meta:
            response.meta['depth'] = 0
            if self.verbose_stats:
                self.stats.inc_value('request_depth_count/0', spider=spider)

        return (r for r in result or () if _filter(r))