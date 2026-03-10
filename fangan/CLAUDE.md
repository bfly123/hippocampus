# Hippocampus Project Notes

## Skills

- `/hippo-g` — Inject `.hippocampus/structure-prompt.md` into the conversation as project context. Provides module layout, key files, and source signatures at a glance.

## LLM API Configuration

- **API Base**: `https://code.newcli.com/claude/aws`
- **API Key**: `sk-ant-oat01-1zXO494m31SWCpVzRd8hEIw73sgTFpppSVAi6K9HX4JdELuqVmqMUwZSM6Yw3h31O-GS4LQQDWFur86iX6zWzXIDBGeHIAA`
- **Always use this API base and key** for all hippo pipeline LLM calls.

## Available Models

- `anthropic/claude-haiku-4-5-20251001`
- `anthropic/claude-sonnet-4-5-20250929`


每次plan 完成后都要发送给codex审核，迭代。 代码修改完后也需要和codex 打分迭代，直至通过。
