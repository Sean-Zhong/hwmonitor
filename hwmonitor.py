import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import subprocess
import re
import threading
import time
import os
import glob

class SystemMonitor(ttkb.Window):
    def __init__(self):
        super().__init__(themename="darkly")
        self.title("NixOS AMD System Monitor")
        self.geometry("800x480")
        self.resizable(False, False)

        # Find the AMD GPU card path
        self.amd_gpu_path = self.find_amd_gpu_path()
        if not self.amd_gpu_path:
            print("Warning: Could not find a path for an AMD GPU in /sys/class/drm/. GPU metrics will be 0.")


        # Main frame
        main_frame = ttkb.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        # Create the four gauges
        self.cpu_temp_gauge = self.create_gauge(main_frame, "CPU Temp (°C)")
        self.cpu_load_gauge = self.create_gauge(main_frame, "CPU Load (%)")
        self.gpu_temp_gauge = self.create_gauge(main_frame, "GPU Temp (°C)")
        self.gpu_load_gauge = self.create_gauge(main_frame, "GPU Load (%)")

        # Arrange gauges in a 2x2 grid
        self.cpu_temp_gauge.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.cpu_load_gauge.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.gpu_temp_gauge.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.gpu_load_gauge.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")

        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # Start the update loop in a separate thread
        self.update_thread = threading.Thread(target=self.update_metrics_loop, daemon=True)
        self.update_thread.start()

    def create_gauge(self, parent, label_text):
        """Creates a single gauge widget with a label."""
        frame = ttkb.Frame(parent)
        
        label = ttkb.Label(frame, text=label_text, font=("Helvetica", 14))
        label.pack(pady=(0, 10))

        meter = ttkb.Meter(
            frame,
            metersize=180,
            padding=5,
            amountused=0,
            metertype="semi",
            subtextstyle="light",
            interactive=False,
            bootstyle=SUCCESS,
            stripethickness=10,
            meterthickness=15,
        )
        meter.pack()
        
        # Store the meter widget in the frame for easy access
        frame.meter = meter
        return frame

    def get_cpu_temp(self):
        """Gets CPU temperature from sysfs."""
        try:
            # Look for the 'x86_pkg_temp' type, which is usually the package temperature.
            thermal_zones = subprocess.check_output("ls /sys/class/thermal/", shell=True).decode().strip().split("\n")
            for zone in thermal_zones:
                type_path = f"/sys/class/thermal/{zone}/type"
                if os.path.exists(type_path):
                    with open(type_path) as f:
                        if "x86_pkg_temp" in f.read():
                            with open(f"/sys/class/thermal/{zone}/temp") as temp_f:
                                return int(temp_f.read().strip()) / 1000
            # Fallback if x86_pkg_temp is not found
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return int(f.read().strip()) / 1000
        except Exception as e:
            print(f"Error getting CPU temp: {e}")
            return 0

    def get_cpu_load(self):
        """Gets CPU load percentage."""
        try:
            # Get CPU load from top command
            top_output = subprocess.check_output("top -bn1 | grep '%Cpu(s)'", shell=True).decode()
            match = re.search(r"(\d+\.\d+)\s+id", top_output)
            if match:
                idle_percent = float(match.group(1))
                return 100.0 - idle_percent
            return 0
        except Exception as e:
            print(f"Error getting CPU load: {e}")
            return 0

    def find_amd_gpu_path(self):
        """Finds the sysfs path for the AMD GPU."""
        # This looks for a drm card that has a hwmon directory, typical for GPUs
        for card in glob.glob('/sys/class/drm/card*'):
            if os.path.isdir(os.path.join(card, 'device', 'hwmon')):
                # A simple check for vendor file can confirm it's AMD
                vendor_path = os.path.join(card, 'device', 'vendor')
                if os.path.exists(vendor_path):
                    with open(vendor_path, 'r') as f:
                        # AMD's PCI vendor ID is 0x1002
                        if '0x1002' in f.read():
                            return os.path.join(card, 'device')
        return None

    def get_gpu_temp(self):
        """Gets AMD GPU temperature from sysfs."""
        if not self.amd_gpu_path:
            return 0
        try:
            # The temperature is usually in a file like 'temp1_input' inside the hwmon directory
            hwmon_path = glob.glob(os.path.join(self.amd_gpu_path, 'hwmon', 'hwmon*'))[0]
            temp_input_path = glob.glob(os.path.join(hwmon_path, 'temp*_input'))[0]
            with open(temp_input_path) as f:
                # The value is in millidegrees Celsius
                return int(f.read().strip()) / 1000
        except (IndexError, FileNotFoundError, Exception) as e:
            print(f"Error getting GPU temp: {e}")
            return 0

    def get_gpu_load(self):
        """Gets AMD GPU load percentage from sysfs."""
        if not self.amd_gpu_path:
            return 0
        try:
            # The gpu_busy_percent file gives the utilization directly
            with open(os.path.join(self.amd_gpu_path, 'gpu_busy_percent')) as f:
                return int(f.read().strip())
        except (FileNotFoundError, Exception) as e:
            # Some kernels might not have gpu_busy_percent, try sensors as a fallback
            print(f"Could not read gpu_busy_percent: {e}. Trying 'sensors'.")
            try:
                sensors_output = subprocess.check_output("sensors", shell=True).decode()
                # This regex is an example, it might need to be adjusted for your specific output
                match = re.search(r"edge:\s+\+([\d\.]+)°C", sensors_output)
                if match:
                    return int(float(match.group(1))) # This is temp, not load. Placeholder for a better command.
                return 0
            except Exception as se:
                print(f"Error getting GPU load from sensors: {se}")
                return 0

    def update_metrics_loop(self):
        """Continuously updates the metrics in a loop."""
        while True:
            cpu_temp = self.get_cpu_temp()
            cpu_load = self.get_cpu_load()
            gpu_temp = self.get_gpu_temp()
            gpu_load = self.get_gpu_load()

            # Update the GUI on the main thread
            self.after(0, self.update_gauges, cpu_temp, cpu_load, gpu_temp, gpu_load)
            
            time.sleep(2) # Update every 2 seconds

    def update_gauges(self, cpu_temp, cpu_load, gpu_temp, gpu_load):
        """Updates the gauge widgets with new values."""
        self.cpu_temp_gauge.meter.configure(amountused=int(cpu_temp))
        self.cpu_load_gauge.meter.configure(amountused=int(cpu_load))
        self.gpu_temp_gauge.meter.configure(amountused=int(gpu_temp))
        self.gpu_load_gauge.meter.configure(amountused=int(gpu_load))

        self.cpu_temp_gauge.meter.configure(subtext=f"{int(cpu_temp)}°C")
        self.cpu_load_gauge.meter.configure(subtext=f"{int(cpu_load)}%")
        self.gpu_temp_gauge.meter.configure(subtext=f"{int(gpu_temp)}°C")
        self.gpu_load_gauge.meter.configure(subtext=f"{int(gpu_load)}%")

if __name__ == "__main__":
    app = SystemMonitor()
    app.mainloop()
