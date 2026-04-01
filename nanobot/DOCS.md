# NanoBot AI Assistant

Ultra-lightweight personal AI assistant powered by [NanoBot](https://github.com/HKUDS/nanobot).

## About

NanoBot is an ultra-lightweight personal AI assistant that delivers core agent functionality
with 99% fewer lines of code. This add-on runs the NanoBot gateway as a Home Assistant add-on,
providing:

- 🤖 AI assistant with tool use capabilities
- 💬 Discord bot integration
- 🔌 OpenAI-compatible API endpoint
- 🧠 Memory and context management
- ⏰ Scheduled tasks (cron)
- 🌐 Web search capabilities

## Configuration

### LLM Provider Settings

- **LLM Provider**: The provider name (e.g., `custom`, `openai`, `anthropic`, `openrouter`)
- **LLM API Key**: Your API key for the LLM provider
- **LLM Base URL**: The base URL for the API endpoint (required for custom providers)
- **LLM Model**: The model to use (e.g., `claude-4.5`, `gpt-4o`)

### Discord Integration

- **Enable Discord**: Toggle Discord bot on/off
- **Discord Bot Token**: Your Discord bot token
- **Discord Channel ID**: Restrict the bot to a specific channel (optional)

### Logging

- **Log Level**: Set to `debug` for troubleshooting

## API Access

The NanoBot gateway exposes an API on port **18790**. You can interact with it using
any HTTP client or the NanoBot CLI.

## Support

- [NanoBot GitHub](https://github.com/HKUDS/nanobot)
- [NanoBot Documentation](https://github.com/HKUDS/nanobot#readme)
