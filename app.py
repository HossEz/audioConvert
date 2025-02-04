import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

# Global variables for status animation.
current_file_name = ""
animation_counter = 0
animation_running = False

# -------------
# File Selection
# -------------
def select_files():
    """Open a file dialog to select audio files and display them in the listbox."""
    file_paths = filedialog.askopenfilenames(
        title="Select Audio Files",
        filetypes=[
            ("Audio Files", "*.mp3 *.wav"),
            ("MP3 Files", "*.mp3"),
            ("WAV Files", "*.wav")
        ]
    )
    file_list.delete(0, tk.END)
    for path in file_paths:
        file_list.insert(tk.END, path)

# -----------------------
# Update Advanced Widgets
# -----------------------
def update_format_settings(*args):
    """
    Adjust advanced settings based on the chosen output format.
    
    For wav:
      - Hide encoding widgets.
      - Update sample rate options to common PCM rates.
      - Show the WAV Bit Depth widget.
      
    For mp3:
      - Hide WAV widgets.
      - Update sample rate options for compressed formats.
      - Show encoding settings (CBR/VBR) via an encoding dropdown.
    """
    fmt = output_format_var.get().lower()
    if fmt == "wav":
        # Hide encoding widgets (only applicable for mp3).
        encoding_label.grid_remove()
        encoding_menu.grid_remove()
        vbr_quality_label.grid_remove()
        vbr_quality_menu.grid_remove()
        bitrate_label.grid_remove()
        bitrate_menu.grid_remove()

        # Update sample rate options for WAV (PCM).
        new_rates = ["44100", "48000", "96000", "192000"]
        sample_rate_var.set(new_rates[0])
        sample_rate_menu["menu"].delete(0, "end")
        for rate in new_rates:
            sample_rate_menu["menu"].add_command(label=rate, command=tk._setit(sample_rate_var, rate))
        # Show the WAV Bit Depth widget.
        wav_bit_depth_label.grid(row=5, column=0, sticky="w", pady=5)
        wav_bit_depth_menu.grid(row=5, column=1, sticky="ew", pady=5)
    elif fmt == "mp3":
        # Hide WAV-specific widgets.
        wav_bit_depth_label.grid_remove()
        wav_bit_depth_menu.grid_remove()
        # Update sample rate options for mp3.
        new_rates = ["22050", "44100", "48000"]
        sample_rate_var.set(new_rates[0])
        sample_rate_menu["menu"].delete(0, "end")
        for rate in new_rates:
            sample_rate_menu["menu"].add_command(label=rate, command=tk._setit(sample_rate_var, rate))
        # Show encoding settings for mp3.
        encoding_label.grid(row=5, column=0, sticky="w", pady=5)
        encoding_menu.grid(row=5, column=1, sticky="ew", pady=5)
        update_encoding_settings()

def update_encoding_settings(*args):
    """
    For mp3, based on the chosen encoding type (VBR or CBR):
      - If "Variable bitrate" is selected, show the VBR Quality drop-down.
      - If "Constant bitrate" is selected, show the Bitrate drop-down.
    """
    if output_format_var.get().lower() != "mp3":
        # Not applicable for wav.
        vbr_quality_label.grid_remove()
        vbr_quality_menu.grid_remove()
        bitrate_label.grid_remove()
        bitrate_menu.grid_remove()
        return

    if encoding_var.get() == "Variable bitrate":
        vbr_quality_label.grid(row=7, column=0, sticky="w", pady=5)
        vbr_quality_menu.grid(row=7, column=1, sticky="ew", pady=5)
        bitrate_label.grid_remove()
        bitrate_menu.grid_remove()
    else:
        bitrate_label.grid(row=7, column=0, sticky="w", pady=5)
        bitrate_menu.grid(row=7, column=1, sticky="ew", pady=5)
        vbr_quality_label.grid_remove()
        vbr_quality_menu.grid_remove()

# --------------------
# Animated Status Update
# --------------------
def animate_status():
    """Update the processing popup label with animated dots."""
    global animation_counter, animation_running
    if processing_popup is None or not animation_running:
        return
    # Cycle through 0 to 3 dots.
    dots = "." * (animation_counter % 4)
    status_text = f"Converting '{current_file_name}'{dots}"
    status_label.config(text=status_text)
    animation_counter += 1
    # Schedule the next update.
    processing_popup.after(500, animate_status)

# --------------------
# Conversion Process
# --------------------
def conversion_process():
    """
    Convert the selected files using the chosen options via ffmpeg.
    Runs in a background thread.
    """
    global current_file_name, animation_running
    fmt = output_format_var.get().lower()
    sample_rate = sample_rate_var.get().strip()
    channel = channel_var.get().strip()  # "Mono" or "Stereo"
    result_dir = "result"
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    # Process each file sequentially.
    for index in range(file_list.size()):
        input_file = file_list.get(index)
        current_file_name = os.path.basename(input_file)
        # (The animate_status function will pick up the new filename.)
        # Build the ffmpeg command.
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(result_dir, base_name + f".{fmt}")
        command = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-ar", sample_rate
        ]
        # Set number of channels.
        if channel.lower() == "mono":
            command.extend(["-ac", "1"])
        elif channel.lower() == "stereo":
            command.extend(["-ac", "2"])
        else:
            command.extend(["-ac", channel])
        
        if fmt == "mp3":
            command.extend(["-c:a", "libmp3lame"])
            if encoding_var.get() == "Variable bitrate":
                command.extend(["-qscale:a", vbr_quality_var.get()])
            else:
                command.extend(["-b:a", bitrate_var.get().strip()])
        elif fmt == "wav":
            # For WAV, use PCM encoding based on selected bit depth.
            depth = wav_bit_depth_var.get().strip()
            if depth == "16":
                codec = "pcm_s16le"
            elif depth == "24":
                codec = "pcm_s24le"
            elif depth == "32":
                codec = "pcm_s32le"
            else:
                codec = "pcm_s16le"
            command.extend(["-c:a", codec])
        else:
            continue  # Unsupported format

        command.append(output_file)
        print("Running command:", " ".join(command))
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            # If an error occurs, destroy the popup and show an error.
            if processing_popup is not None:
                processing_popup.destroy()
            messagebox.showerror("Conversion Error", f"Failed to convert:\n{input_file}\nError: {e}")
            return

    # After finishing all files, stop the animation and close the popup.
    animation_running = False
    if processing_popup is not None:
        processing_popup.destroy()
    messagebox.showinfo("Done", "All files have been successfully converted.")

def start_conversion():
    """
    Start the conversion process in a background thread and display a processing popup.
    """
    global processing_popup, animation_running, current_file_name, animation_counter
    processing_popup = tk.Toplevel(root)
    processing_popup.title("Processing")
    # Create a label for the animated status message.
    global status_label
    status_label = tk.Label(processing_popup, text="Preparing...", padx=20, pady=20)
    status_label.pack()
    processing_popup.resizable(False, False)
    processing_popup.geometry("+%d+%d" % (root.winfo_rootx()+50, root.winfo_rooty()+50))
    root.attributes("-disabled", True)

    # Initialize the animation globals.
    current_file_name = ""
    animation_counter = 0
    animation_running = True
    animate_status()  # Start the animation

    def reenable_main():
        root.attributes("-disabled", False)

    def thread_finished():
        reenable_main()

    conv_thread = threading.Thread(target=lambda: [conversion_process(), root.after(0, thread_finished)])
    conv_thread.start()

# -------------------------
# Build the GUI
# -------------------------
root = tk.Tk()
root.title("Audio Converter")

processing_popup = None

frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

# Row 0: File selection button.
select_button = tk.Button(frame, text="Select Files", command=select_files)
select_button.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))

# Row 1: Listbox with selected files.
file_list = tk.Listbox(frame, width=80, height=10)
file_list.grid(row=1, column=0, columnspan=2, pady=(0, 10))

# Row 2: Output Format.
tk.Label(frame, text="Output Format:").grid(row=2, column=0, sticky="w", pady=5)
output_format_options = ["mp3", "wav"]
output_format_var = tk.StringVar(value=output_format_options[0])
output_format_menu = tk.OptionMenu(frame, output_format_var, *output_format_options)
output_format_menu.grid(row=2, column=1, sticky="ew", pady=5)
output_format_var.trace("w", update_format_settings)

# Row 3: Sample Rate.
tk.Label(frame, text="Sample Rate (Hz):").grid(row=3, column=0, sticky="w", pady=5)
# Options will be updated by update_format_settings.
sample_rate_options = ["22050", "44100", "48000"]
sample_rate_var = tk.StringVar(value=sample_rate_options[0])
sample_rate_menu = tk.OptionMenu(frame, sample_rate_var, *sample_rate_options)
sample_rate_menu.grid(row=3, column=1, sticky="ew", pady=5)

# Row 4: Channel.
tk.Label(frame, text="Channel:").grid(row=4, column=0, sticky="w", pady=5)
channel_options = ["Mono", "Stereo"]
channel_var = tk.StringVar(value="Mono")
channel_menu = tk.OptionMenu(frame, channel_var, *channel_options)
channel_menu.grid(row=4, column=1, sticky="ew", pady=5)

# --- Widgets for WAV ---
wav_bit_depth_label = tk.Label(frame, text="Bit Depth (WAV):")
wav_bit_depth_options = ["16", "24", "32"]
wav_bit_depth_var = tk.StringVar(value="16")
wav_bit_depth_menu = tk.OptionMenu(frame, wav_bit_depth_var, *wav_bit_depth_options)

# --- Widgets for mp3 ---
# Encoding (VBR/CBR) Option
encoding_label = tk.Label(frame, text="Encoding:")
encoding_options = ["Variable bitrate", "Constant bitrate"]
encoding_var = tk.StringVar(value="Variable bitrate")
encoding_menu = tk.OptionMenu(frame, encoding_var, *encoding_options)
encoding_var.trace("w", update_encoding_settings)

# For CBR, use a drop-down for common bitrates.
bitrate_label = tk.Label(frame, text="Bitrate (for CBR):")
bitrate_options = ["80k", "96k", "128k", "192k", "256k", "320k"]
bitrate_var = tk.StringVar(value=bitrate_options[0])
bitrate_menu = tk.OptionMenu(frame, bitrate_var, *bitrate_options)

# For VBR, use a drop-down for quality settings (0-9).
vbr_quality_label = tk.Label(frame, text="VBR Quality (0-9):")
vbr_quality_options = [str(i) for i in range(0, 10)]
vbr_quality_var = tk.StringVar(value="7")
vbr_quality_menu = tk.OptionMenu(frame, vbr_quality_var, *vbr_quality_options)

# Place the Convert button.
convert_button = tk.Button(frame, text="Convert", command=start_conversion)
convert_button.grid(row=8, column=0, columnspan=2, pady=(10, 0), sticky="ew")

# Initialize widgets according to the default format.
update_format_settings()

root.mainloop()
