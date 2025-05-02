import logging
import os
import sentry_sdk

import sapcc_sentrylogger.handler
from unittest import TestCase, mock
from unittest.mock import patch
from sapcc_sentrylogger.handler import (
    EventHandler,
    BreadcrumbHandler,
    is_client_initialized,
)


class SentryHandlerTest(TestCase):

    def setUp(self):
        super(SentryHandlerTest, self).setUp()

    @patch.object(sentry_sdk, "init", return_value=None)
    def test_init_sdk_not_called(self, mock_init):
        """test if sentry sdk does not get initialized when SENTRY_DSN is not set"""
        self.assertNotIn(
            "SENTRY_DSN", os.environ, "Unittests cannot run with SENTRY_DSN set!"
        )
        _e = EventHandler()
        _b = BreadcrumbHandler()
        mock_init.assert_not_called()

    @patch.object(sapcc_sentrylogger.handler, "_init_client", return_value=None)
    @patch.dict(os.environ, {"SENTRY_DSN": "foo"})
    def test_init_sdk_called_for_events(self, mock_init):
        """ensure the event handler calls the custom init method when SENTRY_DSN is set"""

        _e = EventHandler()
        mock_init.assert_called_once()

    @patch.object(sapcc_sentrylogger.handler, "_init_client", return_value=None)
    @patch.dict(os.environ, {"SENTRY_DSN": "foo"})
    def test_init_sdk_called_for_breadcrumbs(self, mock_init):
        """ensure the breadcrumb handler calls the custom init method when SENTRY_DSN is set"""

        _b = BreadcrumbHandler()
        mock_init.assert_called_once()

    def disabled_test_init_sdk_not_called_by_default(self):
        """importing the sdk should not initialize the client"""
        self.assertEqual(is_client_initialized(), False)

    @patch.object(sentry_sdk.integrations.logging.EventHandler, "emit")
    def test_logging_error_message(self, mock_emit):
        """Ensure that the original sentry event Handler gets executed"""
        import logging

        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.ERROR)

        sentry_handler = EventHandler()
        sentry_handler.setLevel(logging.ERROR)

        logger.addHandler(sentry_handler)

        logger.error("Test Message")
        mock_emit.assert_called_once()

    def test_helpers_trueish(self):

        from sapcc_sentrylogger.handler import _bool_env

        with patch.dict(os.environ, {"BOOLTEST": "foo"}):
            self.assertTrue(_bool_env("BOOLTEST", True))
            self.assertFalse(_bool_env("BOOLTEST", False))

        with patch.dict(os.environ, {"BOOLTEST": "True"}):
            self.assertTrue(_bool_env("BOOLTEST", False))

        with patch.dict(os.environ, {"BOOLTEST": "False"}):
            self.assertFalse(_bool_env("BOOLTEST", True))

    def test_helpers_sanitize_dsn_raven_rewrite(self):

        from sapcc_sentrylogger.handler import _sanitize_dsn

        expected = "https://user:pass@fqdn/123"
        dsn = f"requests+{expected}?foo=bar"
        self.assertEqual(expected, _sanitize_dsn(dsn))

    def test_helpers_sanitize_dsn_noop(self):

        from sapcc_sentrylogger.handler import _sanitize_dsn

        expected = "https://user:pass@fqdn/123"
        self.assertEqual(expected, _sanitize_dsn(expected))

    @mock.patch.dict(
        os.environ,
        {
            "SENTRY_DSN": "http://foo:bar@127.0.0.1:9999/123",
            "CCSENTRY_DEBUG": "true",
            "CCSENTRY_AUTO_ENABLE_LOG": "false",
            "CCSENTRY_AUTO_INTEGRATIONS": "false",
        },
    )
    def test_helpers_integrations_defaults_only(self):
        """test if we can skip the logging integration and
        if the sdk get initialized. We need to combine
        several tests here, as initializing the sdk will
        create global state and tests are running concurrently.
        """

        from sapcc_sentrylogger.handler import _init_client

        # we need to disable the AtExit integration, as it will throw
        # an expection during testing when the tests are done because
        # it will try writing to an already closed logger stream when
        # we capture the logger output
        sentry_sdk.integrations._DEFAULT_INTEGRATIONS.remove(
            "sentry_sdk.integrations.atexit.AtexitIntegration"
        )

        # check that we have successfully initialized the client and that
        # it was not already initialized before
        with self.assertLogs(level=logging.DEBUG) as captured:
            self.assertTrue(_init_client())

        # check if the monkey patching was successful:
        from sentry_sdk.integrations import iter_default_integrations

        default_integrations = list(iter_default_integrations(False))
        our_integrations_names = set(
            [f"{c.__module__}.{c.__name__}" for c in default_integrations]
        )

        logging_integration_name = "sentry_sdk.integrations.logging.LoggingIntegration"
        self.assertNotIn(logging_integration_name, our_integrations_names)

        # now check the sentry sdk log output so we ensure that the sdk
        # is actually initialized and loading its integrations - but not the logging
        # integration
        messages = [record.getMessage() for record in captured.records]
        self.assertIn("Setting up integrations (with default = True)", messages)
        self.assertNotIn("Enabling integration logging", messages)
