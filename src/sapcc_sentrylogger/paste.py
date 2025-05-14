from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware


def sapcc_sentry_filter_factory(global_conf, **kwargs):
    use_x_forwarded_for = kwargs.pop("use_x_forwarded_for", False)
    def filter(app):
        return SentryWsgiMiddleware(app, use_x_forwarded_for=use_x_forwarded_for)
    return filter
