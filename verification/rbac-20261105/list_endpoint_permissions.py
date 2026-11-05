import django, json
django.setup()
from django.urls import URLPattern, URLResolver, get_resolver
from accounts.rbac import required_capability
from config.business_access import PUBLIC_NAMES


def walk(patterns, prefix='', namespace=''):
    for item in patterns:
        route = prefix + str(item.pattern)
        if isinstance(item, URLResolver):
            yield from walk(item.url_patterns, route, namespace + (item.namespace + ':' if item.namespace else ''))
        elif item.name:
            name = namespace + item.name
            yield {'route': route, 'name': name, 'GET': 'public' if name in PUBLIC_NAMES else required_capability(name), 'POST': 'public + CSRF/form checks' if name in PUBLIC_NAMES else required_capability(name, 'POST')}


rows = list(walk(get_resolver().url_patterns))
assert not [row for row in rows if row['GET'] is None]
print(json.dumps(rows, ensure_ascii=False, indent=2))
