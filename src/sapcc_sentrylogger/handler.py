"""
Copyright 2024 SAP SE or an SAP affiliate company and sapcc_sentrylogger contributors.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this 
file except in compliance with the License. 

You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR 
CONDITIONS OF ANY KIND, either express or implied. See the License for the 
specific language governing permissions and limitations under the License.

"""

import os
from typing import Sequence

import sentry_sdk

from logging import getLogger
from sentry_sdk.consts import VERSION
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.logging import EventHandler as SentryEventHandler
from sentry_sdk.integrations.logging import BreadcrumbHandler as SentryBreadcrumbHandler

logger = getLogger(__name__)


def version_to_tuple(version):
    return tuple(map(int, version.split(".")))


_client_initialized = False


def _sanitize_dsn(dsn) -> str:
    """sanitize the DSN when migrating from raven

    The DSN can have requests+https as schema and supports additional options,
    e.g., to skip ssl verification. We need to remove both for sentry_sdk
    """

    # removeprefix is introduced in python 3.9
    prefix = "requests+"
    if dsn.startswith(prefix):
        _, dsn = dsn.split(prefix, 1)

    if "?" in dsn:
        dsn, _ = dsn.rsplit("?", 1)

    return dsn


def _bool_env(key: str, default: bool) -> bool:
    """get value of environment variable 'key' and parse it to a boolean.
    returns default value if variable is not present or cannot be parsed.
    """
    value = os.getenv(key)
    if not value:
        return default
    if value.strip().lower() in ("y", "yes", "true", "1", "t"):
        return True
    if value.strip().lower() in ("n", "no", "false", "0", "f"):
        return False
    return default


def _init_client() -> bool:
    """init the sentry_sdk client if needed. If it is already enabled, check if
    this was by calling this helper, and print an error. In case some import or
    config change etc. enables it we will at least notice.
    Also errors go to stderr, in case logging is broken.
    """
    global _client_initialized
    if _client_initialized:
        # client already initialized, nothing done
        return False

    if is_client_initialized():
        logger.error("Sentry client was not initialized by sapcc_sentrylogger!")
        return False

    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        # there is an explicit setting to load our handlers, but no sentry dsn, warn the user
        logger.warning("NOTICE: SENTRY_DSN not set, sentry will not be enabled!")
        return False

    # see https://docs.sentry.io/platforms/python/configuration/options/ for a complete list of
    # init parameters, in case we want to configure more -- note we are not using the latest release!

    dsn = _sanitize_dsn(dsn)
    debug = _bool_env(
        "CCSENTRY_DEBUG", False
    )  # that should do the same as SENTRY_DEBUG from the sdk

    # by default enable all default integrations, e.g. sentry_sdk.integrations.excepthook.ExcepthookIntegration,
    enable_default_integrations = _bool_env("CCSENTRY_DEFAULT_INTEGRATIONS", True)
    # ... except the LoggingIntegration
    enable_logging_integration = _bool_env(
        "CCSENTRY_AUTO_ENABLE_LOG", False
    )  # I am open for better variable names...

    # by default disable all auto enabling integrations (e.g. sentry_sdk.integrations.flask.FlaskIntegration)
    auto_enable_integrations = _bool_env("CCSENTRY_AUTO_INTEGRATIONS", False)

    # Background:
    #
    # Using the default Sentry LoggingIntegration is not compatible with our usecase, as we only want specific
    # loggers to send events to sentry.
    #
    # According to the source code the integration overwrites the callHandlers of standard logging library:
    # logging.Logger.callHandlers = sentry_patched_callhandlers
    # Source: https://github.com/getsentry/sentry-python/blob/200d0cdde8eed2caa89b91db8b17baabe983d2de/sentry_sdk/integrations/logging.py#L111
    #
    # It is enough to configure the Event and Breadcrumb handlers via log.ini, calling the handler(s) then happens
    # via the standard python logging library. We need to wrap them, however, to initialize the sdk with our options and
    # prevent the default logging integration to be automatically installed - as it would then be active for all loggers.
    #
    # Additionally sentry_sdk ships with other auto-enabling integrations, that we want to be able to disable by default as well.
    #
    # Note: Setting default_integrations to False disables all default integrations as well as all auto-enabling integrations,
    # unless they are specifically added in the integrations option ... (https://docs.sentry.io/platforms/python/configuration/options/)
    #
    # While we do not want to enable the LoggingIntegration by default, we do want to enable all other default integrations,
    # e.g., the ExceptHookIntegration - not to be confused with the auto-enabling integrations.
    #
    # For that we need to do some monkey patching of the internal list of integrations in sentry_sdk, because
    # the disabled_integrations parameter was added in sentry-sdk==2.11.0 - which we cannot use.
    # also see:
    # https://github.com/getsentry/sentry-python/blob/282b8f7fae3da3c3ec26e5ee5e1599fc74661a72/sentry_sdk/integrations/__init__.py#L100

    if not enable_logging_integration:
        try:
            sentry_sdk.integrations._DEFAULT_INTEGRATIONS.remove(
                "sentry_sdk.integrations.logging.LoggingIntegration"
            )  # noqa
        except ValueError:
            # otherwise tests will fail
            pass

    integrations: Sequence[Integration] = []
    # at this point we have no support for enabling/disabling specific integrations, but here would be the
    # point to add them - note they need to be instances of the respective classes.
    # in case we need it, here is how it is done by upstream:
    # https://github.com/getsentry/sentry-python/blob/282b8f7fae3da3c3ec26e5ee5e1599fc74661a72/sentry_sdk/integrations/__init__.py#L46

    sentry_sdk.init(
        integrations=integrations,
        default_integrations=enable_default_integrations,
        auto_enabling_integrations=auto_enable_integrations,
        debug=debug,
        dsn=dsn,
    )

    _client_initialized = True
    return True


def is_client_initialized():
    if version_to_tuple(VERSION) > version_to_tuple("1.45.1"):
        return True if sentry_sdk.get_client() is not None else False
    else:
        hub = sentry_sdk.Hub.current
        return True if hub.client is not None else False


class EventHandler(SentryEventHandler):
    """
    The Sentry library 'raven' is long deprecated.
    Relying on the new standard Sentry EventHandler does not work, as the way
    it initializes the sentry client is not configurable
    This Handler mimics the 'raven' behavior and does a custom initialization of the client.
    """

    def __init__(self):
        _init_client()
        super().__init__()


class BreadcrumbHandler(SentryBreadcrumbHandler):
    """
    The Sentry library 'raven' is long deprecated.
    Relying on the new standard Sentry BreadcrumbHandler does not work, as the way
    it initializes the sentry client is not configurable
    This Handler mimics the 'raven' behavior and does a custom initialization of the client.
    """

    def __init__(self):
        _init_client()
        super().__init__()
