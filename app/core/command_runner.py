"""Threaded, multi-vendor command execution against many devices at once
using Netmiko. Designed to scale from a handful of lab devices up to
~100+ concurrent sessions (bounded by max_workers). Optionally tunnels
all device connections through an SSH jump/bastion host."""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from threading import Event
from typing import List, Callable, Optional

import paramiko
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from ntc_templates.parse import parse_output

from app.core.vendors import to_netmiko_type
from app.core.device_manager import Device
from app.core.jump_server import JumpServerConfig
from app.config import DEFAULT_SSH_TIMEOUT, DEFAULT_MAX_WORKERS, KNOWN_HOSTS_FILE


class JumpServerError(Exception):
    """Raised when the automation server itself cannot be reached."""


@dataclass
class DeviceResult:
    device_name: str
    host: str
    success: bool
    output: str
    duration_seconds: float
    error: str = ""
    raw_output: str = ""


def _run_single_command(conn, cmd: str, timeout: int) -> tuple[str, str]:
    """Capture raw CLI text once, then parse that text for the GUI display."""
    raw = str(conn.send_command(cmd, read_timeout=timeout, use_textfsm=False))
    try:
        parsed = parse_output(
            platform=conn.device_type,
            command=cmd,
            data=raw,
            try_fallback=True,
        )
    except Exception:
        parsed = raw

    if isinstance(parsed, (list, dict)):
        return json.dumps(parsed, indent=2, default=str), raw
    return str(parsed), raw


def open_jump_transport(jump_config: JumpServerConfig, timeout: int = DEFAULT_SSH_TIMEOUT) -> paramiko.SSHClient:
    """Open and authenticate a single SSH session to the automation server.
    The returned client's transport is reused to open one proxied channel
    per device, so we only log into the jump host once per bulk run."""
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    if KNOWN_HOSTS_FILE.exists():
        client.load_host_keys(str(KNOWN_HOSTS_FILE))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(
            hostname=jump_config.host,
            port=jump_config.port,
            username=jump_config.username,
            password=jump_config.get_password(),
            timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )
    except Exception as exc:
        raise JumpServerError(f"Could not connect to automation server {jump_config.host}: {exc}") from exc
    return client


def run_commands_on_device(
    device: Device,
    commands: List[str],
    timeout: int = DEFAULT_SSH_TIMEOUT,
    jump_transport: Optional[paramiko.Transport] = None,
    cancel_event: Optional[Event] = None,
) -> DeviceResult:
    start = time.monotonic()
    if cancel_event and cancel_event.is_set():
        return DeviceResult(device.name, device.host, False, "", 0.0, "Cancelled by operator")
    connection_params = {
        "device_type": to_netmiko_type(device.vendor),
        "host": device.host,
        "port": device.port,
        "username": device.username,
        "password": device.get_password(),
        "timeout": timeout,
        "fast_cli": False,
        "ssh_strict": True,
        "system_host_keys": True,
        "alt_host_keys": KNOWN_HOSTS_FILE.exists(),
    }
    if KNOWN_HOSTS_FILE.exists():
        connection_params["alt_key_file"] = str(KNOWN_HOSTS_FILE)
    secret = device.get_secret()
    if secret:
        connection_params["secret"] = secret

    if jump_transport is not None:
        # Proxy this device's SSH session through the jump host instead of
        # connecting to it directly from this machine.
        try:
            channel = jump_transport.open_channel(
                "direct-tcpip", (device.host, device.port), ("127.0.0.1", 0), timeout=timeout,
            )
        except Exception as exc:
            duration = time.monotonic() - start
            return DeviceResult(device.name, device.host, False, "", duration, f"Automation server tunnel failed: {exc}")
        connection_params["sock"] = channel

    output_chunks = []
    raw_output_chunks = []
    try:
        with ConnectHandler(**connection_params) as conn:
            if secret:
                conn.enable()
            for cmd in commands:
                if cancel_event and cancel_event.is_set():
                    duration = time.monotonic() - start
                    return DeviceResult(
                        device.name, device.host, False, "\n".join(output_chunks), duration,
                        "Cancelled by operator", "\n".join(raw_output_chunks),
                    )
                result, raw_result = _run_single_command(conn, cmd, timeout)
                output_chunks.append(f"--- {cmd} ---\n{result}\n")
                raw_output_chunks.append(
                    f"====================================\n"
                    f"COMMAND: {cmd}\n"
                    f"====================================\n"
                    f"{raw_result}\n"
                )
        duration = time.monotonic() - start
        return DeviceResult(
            device_name=device.name,
            host=device.host,
            success=True,
            output="\n".join(output_chunks),
            duration_seconds=duration,
            raw_output="\n".join(raw_output_chunks),
        )
    except NetmikoAuthenticationException as exc:
        duration = time.monotonic() - start
        return DeviceResult(device.name, device.host, False, "", duration, f"Authentication failed: {exc}")
    except NetmikoTimeoutException as exc:
        duration = time.monotonic() - start
        message = str(exc)
        if "not found in known_hosts" in message:
            message = f"SSH host-key error: {message} Add the verified key for {device.host} to the application known_hosts file."
        else:
            message = f"Connection timed out: {message}"
        return DeviceResult(device.name, device.host, False, "", duration, message)
    except paramiko.SSHException as exc:
        duration = time.monotonic() - start
        return DeviceResult(
            device.name,
            device.host,
            False,
            "",
            duration,
            f"SSH host-key or protocol error: {exc}",
        )
    except Exception as exc:  # noqa: BLE001 - surface any driver/vendor error to the UI
        duration = time.monotonic() - start
        return DeviceResult(device.name, device.host, False, "", duration, str(exc))


def run_bulk(
    devices: List[Device],
    commands: List[str],
    max_workers: int = DEFAULT_MAX_WORKERS,
    timeout: int = DEFAULT_SSH_TIMEOUT,
    on_result: Optional[Callable[[DeviceResult], None]] = None,
    jump_config: Optional[JumpServerConfig] = None,
    cancel_event: Optional[Event] = None,
) -> List[DeviceResult]:
    """Run `commands` against every device in `devices` concurrently.

    `on_result` is invoked (from a worker thread) as each device finishes,
    so a GUI can stream progress instead of waiting for the whole batch.

    If `jump_config` is provided and enabled, a single SSH session to the
    jump/bastion host is opened up front and reused (one proxied channel
    per device) for the whole run, rather than reconnecting per device.
    Raises JumpServerError if the jump host itself can't be reached.
    """
    jump_client = None
    jump_transport = None
    if jump_config and jump_config.enabled:
        jump_client = open_jump_transport(jump_config, timeout=timeout)
        jump_transport = jump_client.get_transport()

    results: List[DeviceResult] = []
    try:
        with ThreadPoolExecutor(max_workers=min(max_workers, max(1, len(devices)))) as pool:
            futures = {
                pool.submit(
                    run_commands_on_device, device, commands, timeout, jump_transport, cancel_event,
                ): device
                for device in devices
            }
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if on_result:
                    on_result(result)
    finally:
        if jump_client:
            jump_client.close()
    return results
