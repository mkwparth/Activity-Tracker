from dataclasses import dataclass, asdict, field
import getpass
import platform
import socket
import time
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
import json
import threading
import uuid
import pygetwindow as gw
from pynput import mouse, keyboard

@dataclass
class Event:
    session_id: str
    timestamp: str
    event_type: str
    data: Dict[str, Any]

    def to_dict(self):
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    

@dataclass
class SessionMetadata:
    session_id: str
    start_time_utc: str
    hostname: str
    username: str
    os: str
    output_file: str    

@dataclass
class ActivityObserver:
    output_dir:Path = Path("./activity_logs")
    mouse_throttle_ms: int = 250 # in ms so 4 events in 1 sec
    window_poll_interval: int = 1

    session: Optional[SessionMetadata] = field(init=False, default=None)
    is_recording: bool = field(init=False, default=False)
    event_count: int = field(init=False, default=0)

    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)
    _log_file: Optional[Any] = field(init=False, default=None)

    _current_window: Dict[str, Any] = field(init=False, default_factory=dict)
    _last_mouse_time: float = field(init=False, default=0.0)

    def __post_init__(self):
        self.output_dir.mkdir(exist_ok=True)

    def _utc_now(self) -> str:
        """Get UTC time now"""
        return datetime.now(timezone.utc).isoformat()
    

    def _window_monitor_loop(self):
        while self.is_recording:
            try:
                win = gw.getActiveWindow()
                if win:
                    self._current_window = {
                        "window_title": win.title,
                        "window_width": win.width,
                        "window_height": win.height,
                    }
                else:
                    self._current_window = {
                        "window_title": None,
                        "window_width": None,
                        "window_height": None
                    }
            except Exception:
                pass

            time.sleep(self.window_poll_interval)
    
    def _get_active_window(self) -> Dict[str,Any]:
        """Get Active Window Info"""
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()

            if win:
                return {
                    "window_title": win.title
                }
        except Exception:
            pass
        return {"window_title": None}

    def start(self):
        """Start logging events"""

        if self.is_recording:
            return
        
        session_id = str(uuid.uuid4())
        start_time = self._utc_now()


        self.session = SessionMetadata(
            session_id=session_id,
            start_time_utc=start_time,
            hostname=socket.gethostname(),
            username=getpass.getuser(),
            os=f"{platform.system()} {platform.release()}",
            output_file=str(self.output_dir / f"session_{session_id}.jsonl")
        )

        print(self.session.hostname, self.session.username, self.session.os)

        self._log_file = open(self.session.output_file, "a", encoding = "utf-8", buffering = 1)
        self.is_recording = True
        self.event_count = 0

        # Start Window Monitor Thread:
        self._window_thread = threading.Thread(
            target=self._window_monitor_loop,
            daemon=True
        )
        self._window_thread.start()

        self.mouse_listener = mouse.Listener(
                                            on_move=self._on_mouse_move,
                                            on_click=self._on_mouse_click,
                                            on_scroll=self._on_mouse_scroll
                                        )
        
        self.keyboard_listener = keyboard.Listener(
                                            on_press=self._on_key_press
                                        )
        self.mouse_listener.start()
        self.keyboard_listener.start()

        print(f"Observer started. Session ID: {self.session.session_id}")


    def stop(self):
        """stop logging events"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        self.mouse_listener.stop()
        self.keyboard_listener.stop()

        if self._log_file:
            self._log_file.close()
        
        print(f"Observer stopped. Total events: {self.event_count}")
        print(f"Data stored in: {self.session.output_file}")

    
    def _write_event(self, event_type:str, payload:Dict[str, Any]):
        if not self.is_recording:
            return
        
        # Using threading: to protects shared writes
        with self._lock:
            event = Event(
                session_id=self.session.session_id,
                timestamp=self._utc_now(),
                event_type=event_type,
                data={**payload, **self._current_window}
            )

            self._log_file.write(event.to_json() + "\n")
            self.event_count += 1

    # mouse handlers
    def _on_mouse_move(self, x, y):
        now = time.time()

        if(now - self._last_mouse_time) * 1000 < self.mouse_throttle_ms:
            return
        
        self._last_mouse_time = now

        self._write_event("mouse_move", {
            "x": x,
            "y": y,
        })


    def _on_mouse_click(self, x, y, button, pressed):
        self._write_event("mouse_click", {
            "x": x,
            "y": y,
            "button": str(button),
            "action": "pressed" if pressed else "released"
        })
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        self._write_event("mouse_scroll", {
            "x": x,
            "y": y,
            "dx": dx,
            "dy": dy
        })


    # keyboard handlers 
    def _on_key_press(self, key):
        try:
            key_str = key.char
        except AttributeError:
            key_str = str(key)
        
        self._write_event("key_press", {"key": key_str})

    # Removing because we don't need key_release event at the moment 
    # def _on_key_release(self, key):
    #     try:
    #         key_str = key.char
    #     except AttributeError:
    #         key_str = str(key)

    #     self._write_event("key_release", {"key": key_str})
    

if __name__ == "__main__":
    observer = ActivityObserver()

    observer.start()

    print("recording for 20 sec....")

    time.sleep(20)
    observer.stop()