"""CLI — the main interface for Situational AI.

Commands:
  start     — Run the coach daemon (checks thresholds on interval)
  log       — Manually log a health metric
  import    — Import Apple Health XML export
  status    — Show current threshold states
  chat      — Chat with an active coach
  config    — View/edit thresholds and settings
"""

from __future__ import annotations

import signal
import sys
import time

import click
from rich.console import Console
from rich.table import Table

from situational_ai.coach import get_coach_response, get_goal_celebration
from situational_ai.config import load_settings, load_user_config, save_user_config
from situational_ai.health_data import get_history, get_latest, import_apple_health_xml, log_manual_entry
from situational_ai.notifier import send_coach_notification
from situational_ai.thresholds import (
    Threshold,
    ThresholdStatus,
    evaluate_threshold,
    get_all_triggered,
)

console = Console()


@click.group()
def main():
    """Situational AI — a health coach that only activates when you need it.

    Runs 100% on your machine. Uses your own API key. Zero server costs.
    """
    pass


@main.command()
@click.argument("xml_path", type=click.Path(exists=True))
def import_health(xml_path: str):
    """Import an Apple Health XML export."""
    console.print(f"[bold]Importing Apple Health data from:[/bold] {xml_path}")
    console.print("[dim]This may take a minute for large exports...[/dim]")

    count = import_apple_health_xml(xml_path)
    console.print(f"[green bold]Done![/green bold] Imported {count:,} health records.")


@main.command()
@click.argument("metric")
@click.argument("value", type=float)
@click.option("--unit", "-u", default="lb", help="Unit of measurement")
def log(metric: str, value: float, unit: str):
    """Log a health metric manually. Example: log body_mass 172 --unit lb"""
    log_manual_entry(metric, value, unit)
    console.print(f"[green]Logged:[/green] {metric} = {value} {unit}")

    # Immediately check thresholds
    config = load_user_config()
    settings = load_settings()
    thresholds = [Threshold.from_dict(t) for t in config["thresholds"]]

    for t in thresholds:
        if t.metric != metric:
            continue
        state = evaluate_threshold(t)
        if state.status == ThresholdStatus.TRIGGERED:
            console.print(f"\n[red bold]⚠ THRESHOLD CROSSED:[/red bold] {metric} {value} {unit} is {t.direction.value} {t.value} {unit}")
            console.print("[yellow]Coach activated. Starting coaching session...[/yellow]\n")
            response = get_coach_response(t, state, settings)
            send_coach_notification(response, t.id, t.metric, state.current_value or value, t.unit, t.goal_value)
        elif state.status == ThresholdStatus.GOAL_MET:
            console.print(f"\n[green bold]🎉 GOAL REACHED![/green bold] {metric} = {value} {unit} (goal: {t.goal_value} {unit})")
            response = get_goal_celebration(t, state, settings)
            send_coach_notification(response, t.id, t.metric, state.current_value or value, t.unit, t.goal_value)


@main.command()
def status():
    """Show current threshold states and latest values."""
    config = load_user_config()
    thresholds = [Threshold.from_dict(t) for t in config["thresholds"]]

    table = Table(title="Situational AI — Threshold Status")
    table.add_column("ID", style="bold")
    table.add_column("Metric")
    table.add_column("Threshold")
    table.add_column("Current")
    table.add_column("Goal")
    table.add_column("Status")

    for t in thresholds:
        state = evaluate_threshold(t)
        latest = get_latest(t.metric)
        current = f"{latest.value} {latest.unit}" if latest else "—"

        status_style = {
            ThresholdStatus.INACTIVE: "[green]Inactive[/green]",
            ThresholdStatus.TRIGGERED: "[red bold]ACTIVE — Coach ON[/red bold]",
            ThresholdStatus.GOAL_MET: "[green bold]Goal Met! 🎉[/green bold]",
        }

        table.add_row(
            t.id,
            t.metric.replace("_", " ").title(),
            f"{t.direction.value} {t.value} {t.unit}",
            current,
            f"{t.goal_value} {t.unit}",
            status_style.get(state.status, str(state.status)),
        )

    console.print(table)


@main.command()
@click.option("--threshold-id", "-t", default=None, help="Which threshold's coach to chat with")
def chat(threshold_id: str | None):
    """Chat with an active coach interactively."""
    config = load_user_config()
    settings = load_settings()
    thresholds = [Threshold.from_dict(t) for t in config["thresholds"]]

    triggered = get_all_triggered(thresholds)
    if not triggered:
        console.print("[green]All clear![/green] No thresholds are currently triggered.")
        console.print("[dim]Log some data first: situational-ai log body_mass 172 --unit lb[/dim]")
        return

    # Pick the threshold to chat with
    if threshold_id:
        match = [(t, s) for t, s in triggered if t.id == threshold_id]
        if not match:
            console.print(f"[red]Threshold '{threshold_id}' is not currently active.[/red]")
            return
        threshold, state = match[0]
    else:
        threshold, state = triggered[0]

    console.print(f"[bold]Chatting with coach for:[/bold] {threshold.metric.replace('_', ' ').title()}")
    console.print(f"[dim]Current: {state.current_value} {threshold.unit} | Goal: {threshold.goal_value} {threshold.unit}[/dim]")
    console.print("[dim]Type 'quit' to exit.[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if user_input.strip().lower() in ("quit", "exit", "q"):
            console.print("[dim]Session ended. Your coach will be back.[/dim]")
            break

        response = get_coach_response(threshold, state, settings, user_message=user_input)
        console.print(f"\n[bold red]Coach:[/bold red] {response}\n")


@main.command()
def start():
    """Start the coach daemon — monitors thresholds and nags you on schedule.

    This runs in the foreground. Use Ctrl+C to stop.
    """
    settings = load_settings()
    provider = settings.get_provider()
    console.print(f"[bold]Situational AI Coach — Starting[/bold]")
    console.print(f"[dim]Provider: {provider} | Check interval: {settings.check_interval_minutes}m | Intensity: {settings.coach_intensity}/10[/dim]")
    console.print(f"[dim]Running on YOUR machine, using YOUR API key. Zero server costs.[/dim]")
    console.print(f"[dim]Press Ctrl+C to stop.[/dim]\n")

    # Graceful shutdown
    running = True

    def handle_signal(sig, frame):
        nonlocal running
        running = False
        console.print("\n[yellow]Shutting down coach...[/yellow]")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while running:
        try:
            config = load_user_config()
            thresholds = [Threshold.from_dict(t) for t in config["thresholds"]]
            triggered = get_all_triggered(thresholds)

            if triggered:
                for threshold, state in triggered:
                    console.print(f"[yellow]Threshold active:[/yellow] {threshold.metric} = {state.current_value} {threshold.unit} (goal: {threshold.goal_value} {threshold.unit})")
                    response = get_coach_response(threshold, state, settings)
                    send_coach_notification(
                        response, threshold.id, threshold.metric,
                        state.current_value or 0, threshold.unit, threshold.goal_value,
                    )
            else:
                console.print(f"[dim]{time.strftime('%I:%M %p')} — All thresholds clear. Watching...[/dim]")

            # Check for goal completions
            for t in thresholds:
                st = evaluate_threshold(t)
                if st.status == ThresholdStatus.GOAL_MET:
                    response = get_goal_celebration(t, st, settings)
                    send_coach_notification(
                        response, t.id, t.metric,
                        st.current_value or 0, t.unit, t.goal_value,
                    )

        except Exception as e:
            console.print(f"[red]Error during check: {e}[/red]")

        # Sleep in small increments so Ctrl+C is responsive
        for _ in range(settings.check_interval_minutes * 60):
            if not running:
                break
            time.sleep(1)

    console.print("[green]Coach stopped. See you next time.[/green]")


@main.command(name="add-threshold")
@click.option("--id", "threshold_id", required=True, help="Unique ID for this threshold")
@click.option("--metric", required=True, help="Health metric (e.g., body_mass, steps, heart_rate)")
@click.option("--direction", type=click.Choice(["above", "below"]), required=True)
@click.option("--value", type=float, required=True, help="Threshold value that triggers the coach")
@click.option("--goal", "goal_value", type=float, required=True, help="Goal value to deactivate the coach")
@click.option("--unit", default="lb", help="Unit of measurement")
def add_threshold(threshold_id: str, metric: str, direction: str, value: float, goal_value: float, unit: str):
    """Add a new threshold. Example: add-threshold --id weight --metric body_mass --direction above --value 170 --goal 165 --unit lb"""
    config = load_user_config()

    # Check for duplicate
    for t in config["thresholds"]:
        if t["id"] == threshold_id:
            console.print(f"[red]Threshold '{threshold_id}' already exists. Remove it first.[/red]")
            return

    config["thresholds"].append({
        "id": threshold_id,
        "metric": metric,
        "direction": direction,
        "value": value,
        "unit": unit,
        "goal_value": goal_value,
        "coach_persona": "You are a relentless but caring health coach. You do NOT let the user off the hook.",
    })
    save_user_config(config)
    console.print(f"[green]Added threshold:[/green] {threshold_id} — coach activates when {metric} goes {direction} {value} {unit}")


@main.command()
@click.argument("metric")
def history(metric: str):
    """Show recent history for a metric."""
    records = get_history(metric, limit=20)
    if not records:
        console.print(f"[dim]No data for '{metric}'. Log some first.[/dim]")
        return

    table = Table(title=f"Recent {metric.replace('_', ' ').title()} History")
    table.add_column("Date", style="dim")
    table.add_column("Value", style="bold")
    table.add_column("Unit")
    table.add_column("Source", style="dim")

    for r in records:
        table.add_row(
            r.recorded_at.strftime("%Y-%m-%d %H:%M"),
            str(r.value),
            r.unit,
            r.source,
        )

    console.print(table)


if __name__ == "__main__":
    main()
