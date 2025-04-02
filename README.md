# Description

With sapcc_sentrylogger we aim at providing a drop in replacement for the deprecated [Raven](https://github.com/getsentry/raven-python)
to migrate to [sentry_sdk](https://github.com/getsentry/sentry-python), the Official Sentry SDK, version 1.45.1.

Sentry SDK (`sentry_sdk`) will automatically enable integrations and try to configure itself. Because we require fine control over the
integrations enabled, but without touching the calling code, we needed a different way to configure the SDK, more aligned to the approach
that raven was using.

Additionally, to make the migration from raven to the sentry_sdk easier, we rewrite the SENTRY_DSN environment variable.


# Features

* all automatic enabling integrations that `sentry_sdk` ships are turned off by default
* default integrations are enabled, except the `LoggingIntegration`
* fine grained configuration of sentry loggers via the usual logger config file
* configuration of `sentry_sd` initialisation via environment variables

# Requirements and Limitations

We currently only support `sentry-sdk==1.45.1` and do not plan on changing that.

# How it works

When referencing the EventHandler or BreadcrumbHandler provided by this python package, the sentry_sdk will be configured by a wrapper,
called from the __init__ methods of these modified Handlers on the first instanciation of one of the Handlers.

This init code will configure the sentry_sdk in a way that disables all automatic or default integrations.
At the same time it will parse the SENTRY_DSN variable and, if needed, will modify it to be compatible with the sentry_sdk.


# Configuration

See the file [example-logging.conf](example-logging.conf) for an example.


## Migrating from raven

tldr; replace the raven sentry handler in the logging config with the EventHandler and BreadcrumbHandler and add both handlers
to the loggers you wish to send to sentry.

```ini
[handlers]
keys=null, stdout, sentry, bread
# add the handlers ^^^^^^^^^^^^^

[handler_sentry]
class=sapcc_sentrylogger.handler.EventHandler
level=DEBUG

[handler_bread]
class=sapcc_sentrylogger.handler.BreadcrumbHandler
level=DEBUG

[logger_some_logger]
qualname=somelogger
propagate=0
handlers=stdout, sentry, bread
#                ^^^^^^^^^^^^^
#              add the handlers here
```


# Contributing

Feel free to open an issue in the github project.

Please note that for code contributions some legal requirements have to be fulfilled.
You can [read about them here](https://github.com/SAP/.github/blob/main/CONTRIBUTING.md).


# Code of Conduct

All members of the project community must abide by the [SAP Open Source Code of Conduct](https://github.com/SAP/.github/blob/main/CODE_OF_CONDUCT.md).
Only by respecting each other we can develop a productive, collaborative community.

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting a project maintainer or the
contact given in the linked document.


# Licensing

Copyright 2024 SAP SE or an SAP affiliate company and sapcc_sentrylogger contributors.
Please see our [LICENSE](LICENSE.md) for copyright and license information. 


