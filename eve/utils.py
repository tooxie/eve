import eve
from flask import current_app as app
import flask
import hashlib
from flask import request
from datetime import datetime, timedelta


class Config(object):
    def __getattr__(self, name):
        try:
            return app.config.get(name)
        except:
            return getattr(eve, name)


config = Config()


class ParsedRequest(object):
    page = 1
    max_results = config.PAGING_DEFAULT
    where = sort = if_modified_since = if_none_match = if_match = None


def parse_request(args=None, headers=None):
        if flask.has_request_context():
            args = request.args
            headers = request.headers

        r = ParsedRequest()

        if args:
            # TODO where and sort should probably be validated and return a
            # 400 if the field is unknown. This validation however should
            # probably be performed at the datalayer level since the format of
            # these args will change depending on db being used. Would also
            # be nice if the 'query syntax' could be decoupled from to the db
            # being used (i.e. mongodb but we use standard old-style querydef
            # syntax). Needs further thinking.
            #
            # Currently if an unknown field is passed, it is ignored
            r.where = args.get('where')
            r.sort = args.get('sort')

            # TODO should probably return a 400 if 'page' is < 1 or non-numeric
            if 'page' in args:
                try:
                    r.page = abs(int(args.get('page'))) or 1
                except ValueError:
                    pass

            # TODO should probably return a 400 if 'max_results' < 1 or
            # non-numeric
            if 'max_results' in args:
                try:
                    r.max_results = abs(int(args.get('max_results'))) or 1
                    if r.max_results > config.PAGING_LIMIT:
                        r.max_results = config.PAGING_LIMIT
                except ValueError:
                    pass

        if headers:
            r.if_none_match = headers.get('If-None-Match')
            r.if_modified_since = weak_date(headers.get('If-Modified-Since'))
            r.if_match = headers.get('If-Match')

        return r


def weak_date(date):
    # TODO handle the case of a date value which is not rounded to 1 second
    return str_to_date(date) + timedelta(seconds=1) if date else None
    #return str_to_date(date) + timedelta()


def str_to_date(string):
    return datetime.strptime(string, config.DATE_FORMAT) if string else None


def date_to_str(date):
    return datetime.strftime(date, config.DATE_FORMAT) if date else None


# TODO should 'title' in collection_link and document_link use url instead
# of resource name?
def collection_link(resource):
    return ("<link rel='collection' title='%s' href='%s' />" %
            (config.URLS[resource], resource_uri(resource)))


def document_link(resource, document_id):
    title = config.DOMAIN[resource].get('item_title',
                                        resource.rstrip('s').capitalize())
    return ("<link rel='self' title='%s' href='%s%s/' />" %
            (title, resource_uri(resource), document_id))


def home_link():
    return "<link rel='parent' title='home' href='%s' />" % config.BASE_URI


def resource_uri(resource):
    return '%s/%s/' % (config.BASE_URI, config.URLS[resource])


def querydef(max_results=config.PAGING_DEFAULT, where=None, sort=None,
             page=None):
    where_part = '&where=%s' % where if where else ''
    sort_part = '&sort=%s' % sort if sort else ''
    page_part = '&page=%s' % page if page > 1 else ''
    max_results_part = 'max_results=%s' % max_results \
        if max_results != config.PAGING_DEFAULT else ''

    return ('?' + ''.join([max_results_part, where_part, sort_part,
                           page_part]).lstrip('&')).rstrip('?')


def document_etag(value):
    h = hashlib.sha1()
    h.update(str(value))
    return h.hexdigest()