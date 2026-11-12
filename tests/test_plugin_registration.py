"""Tests for plugin registration with Hermes context."""
import unittest
from unittest.mock import MagicMock
from hindsight_project_indexer import register


class TestPluginRegistration(unittest.TestCase):
    def test_register(self):
        mock_ctx = MagicMock()
        register(mock_ctx)

        self.assertTrue(mock_ctx.register_system_prompt_section.called)
        self.assertTrue(mock_ctx.register_hook.called)
        self.assertTrue(mock_ctx.register_command.called)
        self.assertTrue(mock_ctx.register_tool.called)


if __name__ == "__main__":
    unittest.main()
