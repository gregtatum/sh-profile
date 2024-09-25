"""
Profile a local command and open it in the Firefox Profiler.

- Pass the command arguments in past the --
  sh-profile -- [command to run]

- Example of timing an install
  sh-profile -- brew upgrade
"""

import shlex
import subprocess
import sys
import argparse
from datetime import datetime
from typing import Any, Tuple, Optional
import http.server
import json
import urllib
import socket
import time
import urllib.parse
import webbrowser
import re

pattern: Optional[re.Pattern] = None


def strip_ansi(string: str) -> str:
    global pattern
    if not pattern:
        pattern = re.compile(r"\x1B\[\d+(;\d+){0,2}m")
    return pattern.sub("", string)


def run_command(command: list[str]) -> list[Tuple[datetime, str]]:
    buffer: list[Tuple[datetime, str]] = []

    process = subprocess.Popen(
        shlex.join(command),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if not process.stdout:
        raise Exception("No process stdout")

    for line in process.stdout:
        # Print without newline
        print(line[:-1])

        # Don't store whitespace
        if line.strip():
            buffer.append((datetime.now(), strip_ansi(line)))

    process.wait()

    return buffer


class UniqueStringArray:
    """
    This ported from the profiler.
    """

    def __init__(self, original_array: Optional[list[str]] = None):
        if original_array is None:
            original_array = []
        self._array: list[str] = original_array[:]
        self._string_to_index: dict[str, int] = {
            string: i for i, string in enumerate(original_array)
        }

    def get_string(self, index: int, els: Optional[str] = None) -> str:
        """Get the string at the given index."""
        if not self.has_index(index):
            if els:
                print(f"index {index} not in UniqueStringArray")
                return els
            raise ValueError(f"index {index} not in UniqueStringArray")
        return self._array[index]

    def has_index(self, index: int) -> bool:
        """Check if the given index exists in the array."""
        return index < len(self._array)

    def has_string(self, s: str) -> bool:
        """Check if the given string exists in the array."""
        return s in self._string_to_index

    def index_for_string(self, s: str) -> int:
        """Get the index for the given string, adding it if it doesn't exist."""
        index = self._string_to_index.get(s)
        if index is None:
            index = len(self._array)
            self._string_to_index[s] = index
            self._array.append(s)
        return index

    def serialize_to_array(self) -> list[str]:
        """Serialize the array to a new list."""
        return self._array[:]


def get_empty_profile():
    return {
        "meta": {
            "interval": 1,
            "startTime": time.time() * 1000.0,
            "abi": "",
            "misc": "",
            "oscpu": "",
            "platform": "",
            "processType": 0,
            "extensions": {"id": [], "name": [], "baseURL": [], "length": 0},
            "categories": get_categories(),
            "product": "sh-profile",
            "stackwalk": 0,
            "toolkit": "",
            "version": 29,
            "preprocessedProfileVersion": 48,
            "appBuildID": "",
            "sourceURL": "",
            "physicalCPUs": 0,
            "logicalCPUs": 0,
            "CPUName": "",
            "symbolicated": True,
            "markerSchema": [get_task_schema()],
        },
        "libs": [],
        "pages": [],
        "threads": [],
    }


def get_categories():
    """
    Colors are listed here:
    https://github.com/firefox-devtools/profiler/blob/ffe2b6af0fbf4f91a389cc31fd7df776bb198034/src/utils/colors.js#L96
    """
    return [
        {
            "name": "sh-profile",
            "color": "lightblue",
            "subcategories": ["Other"],
        },
    ]


def get_empty_thread():
    """
    https://github.com/firefox-devtools/profiler/blob/ffe2b6af0fbf4f91a389cc31fd7df776bb198034/src/profile-logic/data-structures.js#L358
    """
    return {
        "processType": "default",
        "processStartupTime": 0,
        "processShutdownTime": None,
        "registerTime": 0,
        "unregisterTime": None,
        "pausedRanges": [],
        "name": "Empty",
        "isMainThread": True,
        "pid": "0",
        "tid": 0,
        "samples": {
            "weightType": "tracing-ms",
            "weight": [],
            "stack": [],
            "time": [],
            "length": 0,
        },
        "markers": {
            "data": [],
            "name": [],
            "startTime": [],
            "endTime": [],
            "phase": [],
            "category": [],
            "length": 0,
        },
        "stackTable": {
            "frame": [],
            "prefix": [],
            "category": [],
            "subcategory": [],
            "length": 0,
        },
        "frameTable": {
            "address": [],
            "inlineDepth": [],
            "category": [],
            "subcategory": [],
            "func": [],
            "nativeSymbol": [],
            "innerWindowID": [],
            "implementation": [],
            "line": [],
            "column": [],
            "length": 0,
        },
        "stringArray": [],
        "funcTable": {
            "isJS": [],
            "relevantForJS": [],
            "name": [],
            "resource": [],
            "fileName": [],
            "lineNumber": [],
            "columnNumber": [],
            "length": 0,
        },
        "resourceTable": {"lib": [], "name": [], "host": [], "type": [], "length": 0},
        "nativeSymbols": {
            "libIndex": [],
            "address": [],
            "name": [],
            "functionSize": [],
            "length": 0,
        },
    }


def get_task_schema():
    """
    This is documented in the profiler:
    Markers: https://github.com/firefox-devtools/profiler/src/types/markers.js
    Schema: https://github.com/firefox-devtools/profiler/blob/df32b2d320cb4c9bc7b4ee988a291afa33daff71/src/types/markers.js#L100
    """
    return {
        "name": "sh-profile",
        "tooltipLabel": "{marker.data.line}",
        "tableLabel": "{marker.data.line}",
        "chartLabel": "{marker.data.line}",
        "display": ["marker-chart", "marker-table", "timeline-overview"],
        "data": [
            {
                "key": "startTime",
                "label": "Start time",
                "format": "string",
            },
            {
                "key": "line",
                "label": "Line",
                "format": "string",
                "searchable": "true",
            },
            {
                "key": "hour",
                "label": "Hour",
                "format": "string",
            },
            {
                "key": "date",
                "label": "Date",
                "format": "string",
            },
            {
                "key": "time",
                "label": "Time",
                "format": "time",
            },
        ],
    }


Profile = dict[str, Any]


def get_timestamp_ms(dt: datetime) -> float:
    return dt.timestamp() * 1000.0


def build_profile(buffer: list[Tuple[datetime, str]]) -> Profile:
    profile = get_empty_profile()

    # Compute and save the profile start time.
    profile_start_time = 0.0
    if buffer:
        profile_start_time = get_timestamp_ms(buffer[0][0])
        profile["meta"]["startTime"] = profile_start_time

    # Create the thread that we'll attach the markers to.
    thread = get_empty_thread()
    thread["name"] = "sh-profile"
    profile["threads"].append(thread)
    thread["isMainThread"] = True
    markers = thread["markers"]

    # Map a category name to its index.
    category_index_dict = {
        category["name"]: index
        for index, category in enumerate(profile["meta"]["categories"])
    }
    string_array = UniqueStringArray()

    # run_end = profile_start_time
    for dt, line in buffer:
        run_start = get_timestamp_ms(dt)
        instant_marker = 0
        markers["startTime"].append(run_start - profile_start_time)
        markers["endTime"].append(None)
        markers["phase"].append(instant_marker)

        # Code to add a duration marker:
        # duration_marker = 1
        # markers["endTime"].append(run_end - profile_start_time)
        # markers["phase"].append(duration_marker)

        # TODO - This may be able to deduce a category.
        markers["category"].append(category_index_dict.get("sh-profile", 0))
        markers["name"].append(string_array.index_for_string("sh-profile"))
        markers["data"].append(
            {
                "type": "sh-profile",
                "name": "sh-profile",
                "line": line,
                "hour": dt.strftime("%H:%M:%S"),
                "date": dt.strftime("%Y-%m-%d"),
            }
        )

        markers["length"] += 1

    thread["stringArray"] = string_array.serialize_to_array()

    return profile


waiting_for_request = True
profile_data: Optional[bytes] = None


def open_profile(profile: Any, command: list[str]) -> None:
    global profile_data
    profile_data = json.dumps(profile).encode("utf-8")

    port = get_free_port()
    json_url = f"http://localhost:{port}"

    webbrowser.open(
        "https://profiler.firefox.com/from-url/"
        + urllib.parse.quote(json_url, safe="")
        + "?name="
        + urllib.parse.quote(" ".join(command), safe="")
    )
    server = http.server.HTTPServer(("", port), ServeFile)

    while waiting_for_request:
        server.handle_request()


class ServeFile(http.server.BaseHTTPRequestHandler):
    """Creates a one-time server that just serves one file."""

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def log_message(self, *args):
        # Disable server logging.
        pass

    def do_HEAD(self):
        self._set_headers()

    def do_GET(self):
        self._set_headers()
        try:
            global profile_data
            self.wfile.write(profile_data)
        except Exception as exception:
            print("Failed to serve the file", exception)
            pass
        global waiting_for_request
        waiting_for_request = False


def get_free_port() -> int:
    # https://stackoverflow.com/questions/1365265/on-localhost-how-do-i-pick-a-free-port-number
    sock = socket.socket()
    sock.bind(("", 0))
    return sock.getsockname()[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a command and buffer output with timestamps."
    )
    parser.add_argument(
        "command", nargs=argparse.REMAINDER, help="The bash command to run."
    )
    args = parser.parse_args()

    command: list[str] = args.command

    if not command:
        parser.print_help()
        sys.exit(1)

    if command[0] != "--":
        print("No -- was found at the start of the command", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    buffer = run_command(command[1:])
    profile = build_profile(buffer)
    open_profile(profile, command)


if __name__ == "__main__":
    main()
