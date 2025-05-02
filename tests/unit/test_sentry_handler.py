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

    def test_helpers_sanitize_dsn_raven_rewrite(self):

        from sapcc_sentrylogger.handler import _sanitize_dsn

        expected = "https://user:pass@fqdn/123"
        dsn = f"requests+{expected}?foo=bar"
        self.assertEqual(expected, _sanitize_dsn(dsn))

    def test_helpers_sanitize_dsn_noop(self):

        from sapcc_sentrylogger.handler import _sanitize_dsn

        expected = "https://user:pass@fqdn/123"
        self.assertEqual(expected, _sanitize_dsn(expected))

    def test_helpers_integrations_defaults_only(self):
        """test if we do not add more integrations than possible"""

        from sentry_sdk.integrations import (
            _DEFAULT_INTEGRATIONS,
        )  # noqa
        from sapcc_sentrylogger.handler import _get_iter_default_integrations

        expected_integrations = set(_DEFAULT_INTEGRATIONS)
        our_integrations = set(
            [
                f"{c.__module__}.{c.__name__}"
                for c in (_get_iter_default_integrations(True)(False))
            ]
        )
        # only without the auto enabling integrations we can test for
        # the sets to be equal. This will also assert the presence of the
        # logging integration
        self.assertEqual(expected_integrations, our_integrations)

    def test_helpers_integrations_logging_disable(self):
        """Test if we can successfully skip the logging integration."""
        from sentry_sdk.integrations import _DEFAULT_INTEGRATIONS  #  noqa
        from sapcc_sentrylogger.handler import _get_iter_default_integrations

        expected_integrations = set(_DEFAULT_INTEGRATIONS)
        our_integrations = set(
            [
                f"{c.__module__}.{c.__name__}"
                for c in (_get_iter_default_integrations(False)(False))
            ]
        )
        # we expect all default integrations except the logging integration
        logging_integration = "sentry_sdk.integrations.logging.LoggingIntegration"
        expected_integrations.remove(logging_integration)
        self.assertNotIn(logging_integration, our_integrations)
        # for good measure check if the others are still present:
        self.assertEqual(expected_integrations, our_integrations)

    def test_helpers_integrations_with_auto(self):
        """test if we do not add more integrations than possible"""

        from sentry_sdk.integrations import (
            _DEFAULT_INTEGRATIONS,
            _AUTO_ENABLING_INTEGRATIONS,
        )  # noqa
        from sapcc_sentrylogger.handler import _get_iter_default_integrations

        all_integrations = set(_DEFAULT_INTEGRATIONS + _AUTO_ENABLING_INTEGRATIONS)
        our_integrations = set(
            [
                f"{c.__module__}.{c.__name__}"
                for c in (_get_iter_default_integrations(True)(True))
            ]
        )
        # we cannot test for equal, because the result depends on the
        # installed pyton packages for the auto enabling ones
        # this make this test a bit silly
        self.assertEqual(0, len(our_integrations - all_integrations))
