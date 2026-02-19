from dataclasses import dataclass, asdict, field
import getpass
import platform
import random
import socket
import time
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
import json
import threading
import uuid
import mss
import pygetwindow as gw
from pynput import mouse, keyboard
import gzip
import shutil
import requests

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
    output_logs_dir:Path = Path("./activity/logs")
    output_screenshots_dir:Path = Path("./activity/screenshots")
    _CAPTURES_PER_HOUR:int = field(init=False, default=4)

    upload_interval_seconds: int = 30  # 5 minutes
    backend_url: str = "http://localhost:8000/generate-upload-url"

    mouse_throttle_ms: int = 250 # In ms so 4 events in 1 sec
    window_poll_interval: int = 1

    session: Optional[SessionMetadata] = field(init=False, default=None)
    is_recording: bool = field(init=False, default=False)
    event_count: int = field(init=False, default=0)

    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)
    _log_file: Optional[Any] = field(init=False, default=None)

    _current_window: Dict[str, Any] = field(init=False, default_factory=dict)
    _last_mouse_time: float = field(init=False, default=0.0)

    # cursor_position
    _last_cursor_pos:tuple = field(init=False, default=(0,0)) 

    # threading stop event
    _stop_event: threading.Event = field(init=False, default_factory=threading.Event)


    def __post_init__(self):
        self.output_logs_dir.mkdir(parents=True,exist_ok=True)
        self.output_screenshots_dir.mkdir(parents=True,exist_ok=True)

    def _utc_now(self) -> str:
        """Get UTC time now"""
        return datetime.now(timezone.utc).isoformat()
    

    def _take_screenshot(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_screenshots_dir / f"screenshot_{timestamp}.png"

        # get the cursor position
        cursor_x, cursor_y = self._last_cursor_pos

        with mss.mss() as sct:
            monitors = sct.monitors
            selected_monitor = None

            for monitor in monitors[1:]:
                left = monitor["left"]
                top = monitor["top"]
                width = monitor["width"]
                height = monitor["height"]

                if (left <= cursor_x < left + width) and (top <= cursor_y < top + height):
                    selected_monitor = monitor
                    break
            
            if selected_monitor is None:
                selected_monitor = monitors[0]
            
            img = sct.grab(selected_monitor)
            mss.tools.to_png(img.rgb, img.size, output=str(filename))
            
        # print(f"Screenshot saved: {filename}")
    
    def _screenshot_scheduler(self):
        print("Screenshot scheduler started:", self._stop_event)
        while not self._stop_event.is_set():

            # Generate 6 random seconds inside the next hour
            random_times = sorted(random.sample(range(20), self._CAPTURES_PER_HOUR))

            hour_start = time.time()

            for offset in random_times:
                if self._stop_event.is_set():
                    break

                target_time = hour_start + offset
                sleep_time = target_time - time.time()

                if sleep_time > 0:
                    self._stop_event.wait(sleep_time)

                if not self._stop_event.is_set():
                    self._take_screenshot()

            # Wait until full hour completes
            remaining = hour_start + 20 - time.time()
            if remaining > 0:
                self._stop_event.wait(remaining)

        print("Screenshot scheduler stopped.")
    

    def _window_monitor_loop(self):
        print("Window monitor started.")

        while not self._stop_event.is_set():
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

            # Instead of time.sleep(), use wait() for responsive shutdown
            self._stop_event.wait(self.window_poll_interval)

        print("Window monitor stopped.")
    
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

        # Threading is start
        self._stop_event = threading.Event()

        self.session = SessionMetadata(
            session_id=session_id,
            start_time_utc=start_time,
            hostname=socket.gethostname(),
            username=getpass.getuser(),
            os=f"{platform.system()} {platform.release()}",
            output_file=str(self.output_logs_dir / f"session_{session_id}.jsonl")
        )

        print(self.session.hostname, self.session.username, self.session.os)

        self._log_file = open(self.session.output_file, "a", encoding = "utf-8", buffering = 1)
        self.is_recording = True
        self.event_count = 0

        # Start Window Monitor Thread:
        window_thread = threading.Thread(
            target=self._window_monitor_loop,
            daemon=True
        )
        window_thread.start()

        # Start Screenshot thread:
        screenshot_thread = threading.Thread(
            target=self._screenshot_scheduler,
            daemon=True
        )
        screenshot_thread.start()

        # File uploading thread
        upload_file_thread = threading.Thread(
            target=self._upload_scheduler,
            daemon=True
        )
        upload_file_thread.start()


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

        self._stop_event.set()

        if self._log_file:
            self._log_file.close()
        
        print(f"Observer stopped. Total events: {self.event_count}")
        print(f"Data stored in: {self.session.output_file}")


    
    # Uploading file logic.
    def _upload_scheduler(self):
        print("Upload scheduler started.")
        while not self._stop_event.is_set():

            # Wait for upload interval OR stop signal
            if self._stop_event.wait(self.upload_interval_seconds):
                break  # stop_event triggered during wait

            if not self.is_recording:
                continue

            try:
                with self._lock:
                    # Save the current file
                    file_path = Path(self.session.output_file)
                    
                    # Close current file safely
                    if self._log_file:
                        self._log_file.flush()
                        self._log_file.close()
                    
                    # Immediately open NEW file
                    new_file = self.output_logs_dir / f"session_{uuid.uuid4()}.jsonl"
                    self.session.output_file = str(new_file)
                    self._log_file = open(new_file, "a", encoding="utf-8", buffering=1)

                # Upload outside lock (important!)
                self._upload_file(file_path)
                   
            except Exception as e:
                print("Upload scheduler error:", e)

        print("Upload scheduler stopped.")


    def _upload_file(self, file_path: Path):
        if not file_path.exists():
            return

        try:
            print(f"Uploading {file_path.name}")

            # Get presigned URL
            response = requests.post(
                self.backend_url,
                json={
                    "user_id": self.session.username,
                    "session_id": self.session.session_id
                }
            )

            if response.status_code != 200:
                print("Failed to get presigned URL:", response.text)
                return

            upload_url = response.json()["upload_url"]
            print("upload_url:", upload_url)

            file_bytes = file_path.read_bytes()

            # Upload RAW file directly
            with open(file_path, "rb") as f:
                upload_response = requests.put(
                    upload_url,
                    data=file_bytes,
                    headers={
                        "Content-Length":str(len(file_bytes))
                    }
                )

            if upload_response.status_code == 200:
                print("Upload successful")
                file_path.unlink()  # delete local file
            else:
                print("Upload failed:", upload_response.text)

        except Exception as e:
            print("Upload error:", e)

    
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

        # store last cursor position
        self._last_cursor_pos = (x,y)

        if(now - self._last_mouse_time) * 1000 < self.mouse_throttle_ms:
            return
        
        self._last_mouse_time = now

        self._write_event("mouse_move", {
            "x": x,
            "y": y
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

    time.sleep(120)
    observer.stop()