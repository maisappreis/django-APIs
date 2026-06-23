import os
import sys
from unittest.mock import patch

from django.test import SimpleTestCase

from utils.env import (
    get_environment,
    get_neon_pooler_host,
    is_development,
    is_production,
    is_test,
)


class EnvironmentTest(SimpleTestCase):
    def test_neon_host_is_converted_to_pooled_endpoint(self):
        self.assertEqual(
            get_neon_pooler_host("ep-example.us-east-2.aws.neon.tech"),
            "ep-example-pooler.us-east-2.aws.neon.tech",
        )
        self.assertEqual(
            get_neon_pooler_host("ep-example-pooler.us-east-2.aws.neon.tech"),
            "ep-example-pooler.us-east-2.aws.neon.tech",
        )
        self.assertEqual(get_neon_pooler_host("database.internal"), "database.internal")
        self.assertIsNone(get_neon_pooler_host(None))

    def test_test_command_has_priority(self):
        with patch.object(sys, "argv", ["manage.py", "test"]):
            with patch.dict(
                os.environ,
                {"ENVIRONMENT": "production"},
                clear=True,
            ):
                self.assertTrue(is_test())
                self.assertEqual(get_environment(), "test")
                self.assertFalse(is_production())

    def test_explicit_environment_has_priority_over_vercel(self):
        with patch.object(sys, "argv", ["manage.py", "runserver"]):
            with patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "development",
                    "VERCEL_ENV": "production",
                },
                clear=True,
            ):
                self.assertEqual(get_environment(), "development")
                self.assertTrue(is_development())

    def test_vercel_environment_is_used_as_fallback(self):
        with patch.object(sys, "argv", ["config/wsgi.py"]):
            with patch.dict(
                os.environ,
                {"VERCEL_ENV": "production"},
                clear=True,
            ):
                self.assertEqual(get_environment(), "production")
                self.assertTrue(is_production())

    def test_defaults_to_development_and_supports_aliases(self):
        with patch.object(sys, "argv", ["manage.py", "runserver"]):
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(get_environment(), "development")

            with patch.dict(os.environ, {"ENVIRONMENT": "prod"}, clear=True):
                self.assertTrue(is_production())
