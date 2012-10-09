from flask import current_app as app
from flask import abort
from eve import LAST_UPDATED, ID_FIELD
from datetime import datetime
from eve.utils import parse_request, document_etag, document_link, \
    collection_link, home_link, querydef, resource_uri


def get(resource):
    documents = list()
    response = dict()
    last_updated = datetime.min

    req = parse_request()
    cursor = app.data.find(resource, req)
    for index, document in enumerate(cursor):
        if document[LAST_UPDATED] > last_updated:
            last_updated = document[LAST_UPDATED]

        document['etag'] = document_etag(document)
        document['link'] = document_link(resource, document[ID_FIELD])

        documents.append(document)

    if req.if_modified_since and len(documents) == 0:
        status = 304
        last_modified = None
    else:
        status = 200
        last_modified = last_updated if last_updated > datetime.min else None
        response[resource] = documents
        response['links'] = paging_links(resource, req, index)

    etag = None
    return response, last_modified, etag, status


def getitem(resource, **lookup):
    response = dict()

    req = parse_request()
    document = app.data.find_one(resource, **lookup)
    if document:
        last_modified = document[LAST_UPDATED]
        etag = document_etag(document)

        if req.if_none_match and etag == req.if_none_match:
            return response, last_modified, etag, 304

        if req.if_modified_since and last_modified <= req.if_modified_since:
            return response, last_modified, etag, 304

        document['link'] = document_link(resource, document[ID_FIELD])
        response[resource] = document
        response['links'] = standard_links(resource)
        return response, last_modified, etag, 200

    abort(404)


def paging_links(resource, req, documents_count):
    paging_links = standard_links(resource)

    if documents_count:
        if req.page * req.max_results < documents_count:
            q = querydef(req.max_results, req.where, req.sort, req.page + 1)
            paging_links.append("<link rel='next' title='next page'"
                                " href='%s%s' />" % (resource_uri(resource),
                                                     q))

        if req.page > 1:
            q = querydef(req.max_results, req.where, req.sort, req.page - 1)
            paging_links.append("<link rel='prev' title='previous page'"
                                " href='%s%s' />" % (resource_uri(resource),
                                                     q))

    return paging_links


def standard_links(resource):
    return [home_link(), collection_link(resource)]