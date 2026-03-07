from rich.console import Console


def handle_config_action(console: Console, action: str, key: str | None, value: str | None) -> None:
    from cortexcode.ai_docs.config import get_api_key, get_config, print_config_status, set_api_key, set_config

    if action == "status":
        print_config_status()
        return

    if action == "list":
        cfg = get_config()
        console.print(f"Provider: {cfg.provider}")
        console.print(f"Model: {cfg.model}")
        console.print(f"Temperature: {cfg.temperature}")
        console.print(f"Max tokens: {cfg.max_tokens}")
        return

    if action == "set":
        if not key or not value:
            console.print("[red]Usage: cortexcode config set <key> <value>[/red]")
            console.print("[dim]Examples:[/dim]")
            console.print("  cortexcode config set openai_api_key sk-...")
            console.print("  cortexcode config set ai_provider anthropic")
            console.print("  cortexcode config set ai_model gpt-4o")
            return

        if key in ["openai_api_key", "anthropic_api_key", "google_api_key"]:
            set_api_key(key.replace("_api_key", ""), value)
            console.print(f"[green]✓[/green] Set {key}")
            return

        if key in ["ai_provider", "ai_model", "ai_temperature", "ai_max_tokens"]:
            cfg = get_config()
            if key == "ai_provider":
                cfg.provider = value
            elif key == "ai_model":
                cfg.model = value
            elif key == "ai_temperature":
                cfg.temperature = float(value)
            elif key == "ai_max_tokens":
                cfg.max_tokens = int(value)
            set_config(cfg)
            console.print(f"[green]✓[/green] Set {key} = {value}")
            return

        console.print(f"[red]Unknown key: {key}[/red]")
        return

    if action == "get":
        if not key:
            console.print("[red]Usage: cortexcode config get <key>[/red]")
            return

        if key in ["openai_api_key", "anthropic_api_key", "google_api_key"]:
            val = get_api_key(key.replace("_api_key", ""))
            if val:
                console.print(f"{key}: {val[:8]}...{val[-4:]}")
            else:
                console.print(f"{key}: (not set)")
            return

        cfg = get_config()
        attr_name = key.replace("ai_", "")
        if hasattr(cfg, attr_name):
            console.print(f"{key}: {getattr(cfg, attr_name)}")
        else:
            console.print(f"[red]Unknown key: {key}[/red]")
