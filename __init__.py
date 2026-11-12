"""Root entrypoint for Hermes plugin discovery."""
from hindsight_project_indexer import register, _system_prompt_section, _on_pre_llm_call, _on_post_tool_call

__all__ = ["register", "_system_prompt_section", "_on_pre_llm_call", "_on_post_tool_call"]
