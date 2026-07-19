#!/usr/bin/env python3
"""Launch and manage the Ryu controller processes used by GART."""

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PORTS = (6654,)
DEFAULT_PID_FILE = Path("/tmp/gart_ryu_controllers.json")


def parse_ports(raw):
    ports = tuple(dict.fromkeys(int(item.strip()) for item in raw.split(",") if item.strip()))
    if not ports or any(port < 1 or port > 65535 for port in ports):
        raise ValueError("ports must contain valid TCP port numbers")
    return ports


class ControllerManager:
    def __init__(self, ports=DEFAULT_PORTS, controller_app="controller.py",
                 log_dir=None, pid_file=DEFAULT_PID_FILE):
        self.ports = tuple(ports)
        self.controller_app = Path(controller_app)
        if not self.controller_app.is_absolute():
            self.controller_app = PROJECT_ROOT / self.controller_app
        self.log_dir = Path(log_dir) if log_dir else PROJECT_ROOT / "logs"
        self.pid_file = Path(pid_file)
        self.processes = {}

    def controller_log_path(self, port):
        return self.log_dir / ("ryu_controller_%d.log" % port)

    @staticmethod
    def _is_running(pid):
        try:
            os.kill(pid, 0)
        except (OSError, ProcessLookupError):
            return False
        return True

    def _load_pids(self):
        if not self.pid_file.exists():
            return {}
        try:
            payload = json.loads(self.pid_file.read_text(encoding="utf-8"))
            return {int(port): int(pid) for port, pid in payload.items()}
        except (OSError, ValueError, TypeError):
            return {}

    def _save_pids(self):
        self.pid_file.write_text(
            json.dumps({port: process.pid for port, process in self.processes.items()}),
            encoding="utf-8",
        )

    def start_controller(self, port):
        if not self.controller_app.is_file():
            raise FileNotFoundError("controller application not found: %s" % self.controller_app)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        command = [
            "ryu-manager",
            "--observe-links",
            "--ofp-tcp-listen-port",
            str(port),
            str(self.controller_app),
        ]
        with self.controller_log_path(port).open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        time.sleep(1)
        if process.poll() is not None:
            raise RuntimeError(
                "controller on port %d exited during startup; see %s"
                % (port, self.controller_log_path(port))
            )
        return process

    def start_all(self):
        active = {
            port: pid for port, pid in self._load_pids().items()
            if self._is_running(pid)
        }
        if active:
            raise RuntimeError("controllers already running: %s" % active)
        try:
            for port in self.ports:
                self.processes[port] = self.start_controller(port)
        except Exception:
            self.stop_all()
            raise
        self._save_pids()

    def stop_all(self, timeout=5.0):
        pids = self._load_pids()
        pids.update({port: process.pid for port, process in self.processes.items()})
        for pid in pids.values():
            if not self._is_running(pid):
                continue
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except ProcessLookupError:
                continue

        deadline = time.time() + timeout
        while time.time() < deadline and any(self._is_running(pid) for pid in pids.values()):
            time.sleep(0.1)

        for pid in pids.values():
            if self._is_running(pid):
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.pid_file.unlink(missing_ok=True)
        self.processes.clear()

    def statuses(self):
        return {
            port: ("running" if self._is_running(pid) else "stopped")
            for port, pid in self._load_pids().items()
        }

    def monitor(self):
        while self.processes:
            exited = [port for port, process in self.processes.items()
                      if process.poll() is not None]
            for port in exited:
                del self.processes[port]
            if self.processes:
                time.sleep(1)


def build_parser():
    parser = argparse.ArgumentParser(description="Manage GART Ryu controllers")
    parser.add_argument("command", choices=("start", "stop", "status", "restart"),
                        nargs="?", default="start")
    parser.add_argument("--ports", default=os.environ.get("CONTROLLER_PORTS", "6654"))
    parser.add_argument("--controller-app", default="controller.py")
    parser.add_argument("--log-dir", default=str(PROJECT_ROOT / "logs"))
    parser.add_argument("--pid-file", default=str(DEFAULT_PID_FILE))
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    manager = ControllerManager(
        ports=parse_ports(args.ports),
        controller_app=args.controller_app,
        log_dir=args.log_dir,
        pid_file=args.pid_file,
    )

    if args.command == "stop":
        manager.stop_all()
        return
    if args.command == "status":
        statuses = manager.statuses()
        if not statuses:
            print("No controllers are registered.")
        for port, status in sorted(statuses.items()):
            print("%d: %s" % (port, status))
        return
    if args.command == "restart":
        manager.stop_all()

    manager.start_all()
    print("Controllers started on ports: %s" % ", ".join(map(str, manager.ports)))
    try:
        manager.monitor()
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop_all()


if __name__ == "__main__":
    main()
