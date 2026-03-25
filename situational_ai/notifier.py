"""Notification system — makes sure the coach message actually reaches you.

Supports multiple channels, all running locally:
- Terminal (rich console output) — always on
- System notification (macOS/Linux) — optional, best effort
- Sound alert — optional
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def notify_terminal(coach_message: str, metric_name: str, current_value: float, unit: str, goal_value: float) -> None:
    """Display a rich coach message in the terminal."""
    header = Text(f"🏋️ COACH — {metric_name.replace('_', ' ').upper()}", style="bold red")
    status = Text(f"Current: {current_value} {unit}  |  Goal: {goal_value} {unit}", style="dim")

    panel = Panel(
        f"{coach_message}\n\n[dim]{status}[/dim]",
        title=f"[bold red]{header}[/bold red]",
        subtitle=f"[dim]{datetime.now().strftime('%I:%M %p')}[/dim]",
        border_style="red",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def notify_system(title: str, message: str) -> None:
    """Send an OS-level notification (best effort, no dependencies required)."""
    try:
        if sys.platform == "darwin":
            # macOS — use osascript
            escaped = message.replace('"', '\\"').replace("'", "\\'")
            subprocess.run(
                ["osascript", "-e", f'display notification "{escaped}" with title "{title}"'],
                capture_output=True,
                timeout=5,
            )
        elif sys.platform == "linux":
            # Linux — use notify-send if available
            subprocess.run(
                ["notify-send", title, message],
                capture_output=True,
                timeout=5,
            )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # Best effort — terminal is the primary channel


def notify_sound() -> None:
    """Play a short alert sound (best effort)."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"], capture_output=True, timeout=3)
        else:
            # Terminal bell as fallback
            print("\a", end="", flush=True)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("\a", end="", flush=True)


def send_coach_notification(
    coach_message: str,
    threshold_id: str,
    metric_name: str,
    current_value: float,
    unit: str,
    goal_value: float,
) -> None:
    """Send a coach message through all available channels."""
    # Terminal — always
    notify_terminal(coach_message, metric_name, current_value, unit, goal_value)

    # System notification — short version
    short_msg = coach_message[:150] + "..." if len(coach_message) > 150 else coach_message
    notify_system("Situational AI Coach", short_msg)

    # Sound
    notify_sound()
