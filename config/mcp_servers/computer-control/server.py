#!/usr/bin/env python3
"""
Computer Control MCP Server
Provides tools for screenshot, mouse, keyboard, and window control.
"""

import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
import pyautogui
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("computer-control")

# Configuration
WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", os.getcwd()))
SCREENSHOT_DIR = WORKSPACE_DIR / ".claude-os" / "screenshots"

# Ensure screenshot directory exists
try:
    SCREENSHOT_DIR = SCREENSHOT_DIR.resolve()
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    raise RuntimeError(f"Failed to create screenshot directory at {SCREENSHOT_DIR}: {e}")

# Configure pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# Get screen size for bounds checking
try:
    SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
except Exception:
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080

# Valid keys whitelist
VALID_KEYS = {
    "enter", "tab", "escape", "backspace", "delete", "space",
    "up", "down", "left", "right", "home", "end",
    "pageup", "pagedown", "shift", "ctrl", "alt", "win",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"
}

# Valid mouse buttons
VALID_BUTTONS = {"left", "right", "middle"}

# Valid scroll directions
VALID_DIRECTIONS = {"up", "down"}

# Valid executable extensions on Windows
VALID_EXECUTABLE_EXTS = {".exe", ".bat", ".cmd"}


@mcp.tool()
def screenshot(region: str = None) -> str:
    """Capture full screen or specified region.

    Args:
        region: Optional region format "x,y,width,height"

    Returns:
        File path of saved screenshot
    """
    try:
        if region:
            parts = region.split(",")
            if len(parts) != 4:
                return "Error: region must be exactly 4 comma-separated integers (x,y,width,height)"
            try:
                x, y, width, height = map(int, parts)
            except ValueError:
                return "Error: region values must be integers"

            if x < 0 or y < 0:
                return "Error: x and y coordinates must be non-negative"
            if width <= 0 or height <= 0:
                return "Error: width and height must be positive"
            if width > 10000 or height > 10000:
                return "Error: width and height must not exceed 10000"

            screenshot = pyautogui.screenshot(region=(x, y, width, height))
        else:
            screenshot = pyautogui.screenshot()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"screen_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename
        screenshot.save(str(filepath))

        return str(filepath)
    except Exception as e:
        return f"Error capturing screenshot: {str(e)}"


@mcp.tool()
def click(x: int, y: int, button: str = "left") -> str:
    """Click at coordinates with specified button.

    Args:
        x: X coordinate
        y: Y coordinate
        button: Mouse button ('left', 'right', 'middle')

    Returns:
        Confirmation message
    """
    try:
        if not isinstance(x, int) or not isinstance(y, int):
            return "Error: coordinates must be integers"
        if x < 0 or y < 0:
            return "Error: coordinates must be non-negative"
        if button not in VALID_BUTTONS:
            return f"Error: button must be one of {VALID_BUTTONS}"
        if x >= SCREEN_WIDTH or y >= SCREEN_HEIGHT:
            return f"Error: coordinates ({x}, {y}) exceed screen bounds ({SCREEN_WIDTH}x{SCREEN_HEIGHT})"

        pyautogui.click(x=x, y=y, button=button)
        return f"Clicked {button} button at ({x}, {y})"
    except Exception as e:
        return f"Error clicking: {str(e)}"


@mcp.tool()
def double_click(x: int, y: int) -> str:
    """Double click at coordinates.

    Args:
        x: X coordinate
        y: Y coordinate

    Returns:
        Confirmation message
    """
    try:
        if not isinstance(x, int) or not isinstance(y, int):
            return "Error: coordinates must be integers"
        if x < 0 or y < 0:
            return "Error: coordinates must be non-negative"
        if x >= SCREEN_WIDTH or y >= SCREEN_HEIGHT:
            return f"Error: coordinates ({x}, {y}) exceed screen bounds ({SCREEN_WIDTH}x{SCREEN_HEIGHT})"

        pyautogui.doubleClick(x=x, y=y)
        return f"Double clicked at ({x}, {y})"
    except Exception as e:
        return f"Error double clicking: {str(e)}"


@mcp.tool()
def right_click(x: int, y: int) -> str:
    """Right click at coordinates.

    Args:
        x: X coordinate
        y: Y coordinate

    Returns:
        Confirmation message
    """
    try:
        if not isinstance(x, int) or not isinstance(y, int):
            return "Error: coordinates must be integers"
        if x < 0 or y < 0:
            return "Error: coordinates must be non-negative"
        if x >= SCREEN_WIDTH or y >= SCREEN_HEIGHT:
            return f"Error: coordinates ({x}, {y}) exceed screen bounds ({SCREEN_WIDTH}x{SCREEN_HEIGHT})"

        pyautogui.rightClick(x=x, y=y)
        return f"Right clicked at ({x}, {y})"
    except Exception as e:
        return f"Error right clicking: {str(e)}"


@mcp.tool()
def type_text(text: str, interval: float = 0.02) -> str:
    """Type text with specified interval between keystrokes.

    Args:
        text: Text to type
        interval: Seconds between keystrokes

    Returns:
        Confirmation message
    """
    try:
        if not isinstance(text, str):
            return "Error: text must be a string"
        if len(text) > 10000:
            return "Error: text length must not exceed 10000 characters"
        if not isinstance(interval, (int, float)):
            return "Error: interval must be a number"
        if interval < 0.0 or interval > 1.0:
            return "Error: interval must be between 0.0 and 1.0"

        pyautogui.typewrite(text, interval=interval)
        return f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}"
    except Exception as e:
        return f"Error typing text: {str(e)}"


@mcp.tool()
def press_key(key: str) -> str:
    """Press a single key.

    Args:
        key: Key name (enter, tab, escape, backspace, etc.)

    Returns:
        Confirmation message
    """
    try:
        if not isinstance(key, str):
            return "Error: key must be a string"
        if key.lower() not in VALID_KEYS:
            return f"Error: key must be one of {sorted(VALID_KEYS)}"

        pyautogui.press(key)
        return f"Pressed key: {key}"
    except Exception as e:
        return f"Error pressing key: {str(e)}"


@mcp.tool()
def hotkey(keys: str) -> str:
    """Press key combination.

    Args:
        keys: Comma-separated keys (e.g., "ctrl,c" or "alt,tab")

    Returns:
        Confirmation message
    """
    try:
        if not isinstance(keys, str):
            return "Error: keys must be a string"

        key_list = [k.strip().lower() for k in keys.split(",")]
        invalid_keys = [k for k in key_list if k not in VALID_KEYS]
        if invalid_keys:
            return f"Error: invalid keys: {invalid_keys}. Valid keys: {sorted(VALID_KEYS)}"

        pyautogui.hotkey(*key_list)
        return f"Pressed hotkey: {keys}"
    except Exception as e:
        return f"Error pressing hotkey: {str(e)}"


@mcp.tool()
def scroll(amount: int, direction: str = "down") -> str:
    """Scroll in specified direction.

    Args:
        amount: Number of scroll clicks
        direction: 'down' or 'up'

    Returns:
        Confirmation message
    """
    try:
        if not isinstance(amount, int):
            return "Error: amount must be an integer"
        if amount <= 0:
            return "Error: amount must be positive"
        if direction not in VALID_DIRECTIONS:
            return f"Error: direction must be one of {VALID_DIRECTIONS}"

        scroll_amount = amount if direction == "down" else -amount
        pyautogui.scroll(scroll_amount)
        return f"Scrolled {direction} by {amount} clicks"
    except Exception as e:
        return f"Error scrolling: {str(e)}"


@mcp.tool()
def drag(from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 0.5) -> str:
    """Drag from one point to another.

    Args:
        from_x: Starting X coordinate
        from_y: Starting Y coordinate
        to_x: Ending X coordinate
        to_y: Ending Y coordinate
        duration: Duration in seconds

    Returns:
        Confirmation message
    """
    try:
        for coord_name, coord in [("from_x", from_x), ("from_y", from_y), ("to_x", to_x), ("to_y", to_y)]:
            if not isinstance(coord, int):
                return f"Error: {coord_name} must be an integer"
            if coord < 0:
                return f"Error: {coord_name} must be non-negative"

        if not isinstance(duration, (int, float)):
            return "Error: duration must be a number"
        if duration < 0.0 or duration > 5.0:
            return "Error: duration must be between 0.0 and 5.0"

        max_x = max(from_x, to_x)
        max_y = max(from_y, to_y)
        if max_x >= SCREEN_WIDTH or max_y >= SCREEN_HEIGHT:
            return f"Error: coordinates exceed screen bounds ({SCREEN_WIDTH}x{SCREEN_HEIGHT})"

        pyautogui.drag(to_x - from_x, to_y - from_y, duration=duration, button="left")
        return f"Dragged from ({from_x}, {from_y}) to ({to_x}, {to_y})"
    except Exception as e:
        return f"Error dragging: {str(e)}"


@mcp.tool()
def get_screen_size() -> str:
    """Return screen width and height.

    Returns:
        JSON string with width and height
    """
    try:
        width, height = pyautogui.size()
        return json.dumps({"width": width, "height": height})
    except Exception as e:
        return f"Error getting screen size: {str(e)}"


@mcp.tool()
def get_active_window() -> str:
    """Return the title of the currently active window.

    Returns:
        Window title
    """
    try:
        window = pyautogui.getActiveWindow()
        if window:
            return window.title
        else:
            return "No active window detected"
    except Exception as e:
        return f"Error getting active window: {str(e)}"


@mcp.tool()
def launch_app(path: str) -> str:
    """Launch an application by path.

    Args:
        path: Path to application executable

    Returns:
        Confirmation message
    """
    try:
        if not isinstance(path, str):
            return "Error: path must be a string"

        path_obj = Path(path).resolve()

        if not path_obj.exists():
            return f"Error: file does not exist: {path_obj}"
        if not path_obj.is_file():
            return f"Error: path is not a file: {path_obj}"

        if os.name == "nt":
            suffix = path_obj.suffix.lower()
            if suffix not in VALID_EXECUTABLE_EXTS:
                return f"Error: invalid executable type. Allowed: {VALID_EXECUTABLE_EXTS}"

        subprocess.Popen([str(path_obj)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Launched application: {path_obj}"
    except Exception as e:
        return f"Error launching application: {str(e)}"


@mcp.tool()
def wait(seconds: float) -> str:
    """Wait for specified seconds.

    Args:
        seconds: Seconds to wait (max 30)

    Returns:
        Confirmation message
    """
    try:
        wait_time = min(seconds, 30.0)
        time.sleep(wait_time)
        return f"Waited {wait_time} seconds"
    except Exception as e:
        return f"Error waiting: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
