import os
import sentry_sdk

import sapcc_sentrylogger.handler
from unittest import TestCase
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

    @patch.object(sentry_sdk, "init", return_value=None)
    @patch.dict(os.environ, {"SENTRY_DSN": "foo"})
    def test_init_sdk_called(self, mock_init):
        """test if sentry sdk get initialized when SENTRY_DSN is set by at least on handler
        as this creates global state in .handler, we cannot test both separately
        """
        _e = EventHandler()
        _b = BreadcrumbHandler()
        mock_init.assert_called_once()

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

    def test_init_sdk_not_called_by_default(self):
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

    def test_helpers_senitize_dsn_raven_rewrite(self):

        from sapcc_sentrylogger.handler import _sanitize_dsn

        expected = "https://user:pass@fqdn/123"
        dsn = f"requests+{expected}?foo=bar"
        self.assertEqual(expected, _sanitize_dsn(dsn))

    def test_helpers_senitize_dsn_noop(self):

        from sapcc_sentrylogger.handler import _sanitize_dsn

        expected = "https://user:pass@fqdn/123"
        self.assertEqual(expected, _sanitize_dsn(expected))

    def test_helpers_integrations_all(self):

        from sentry_sdk.integrations import (
            _DEFAULT_INTEGRATIONS,
            _AUTO_ENABLING_INTEGRATIONS,
        )  # noqa
        from sapcc_sentrylogger.handler import _get_integrations

        all_integrations = _DEFAULT_INTEGRATIONS + _AUTO_ENABLING_INTEGRATIONS

        # _get_integrations(enable_defaults, enable_logging, enable_auto)
        self.assertEqual(all_integrations, _get_integrations(True, True, True))

    def test_helpers_integrations_defaults_only(self):

        from sentry_sdk.integrations import _DEFAULT_INTEGRATIONS  # noqa
        from sapcc_sentrylogger.handler import _get_integrations

        # _get_integrations(enable_defaults, enable_logging, enable_auto)
        self.assertEqual(_DEFAULT_INTEGRATIONS, _get_integrations(True, True, False))

    def test_helpers_integrations_logging_disable(self):

        from sapcc_sentrylogger.handler import _get_integrations

        self.assertIn(
            "sentry_sdk.integrations.logging.LoggingIntegration",
            _get_integrations(True, True, True),
        )
        # _get_integrations(enable_defaults, enable_logging, enable_auto)
        self.assertNotIn(
            "sentry_sdk.integrations.logging.LoggingIntegration",
            _get_integrations(True, False, True),
        )
