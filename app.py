import os
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import tkinter as tk  # for standard Listbox

# Set CustomTkinter appearance to Dark mode and use the dark-blue theme.
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# -------------------------------
# Global Variables for Animation
# -------------------------------
current_file_name = ""
animation_counter = 0
animation_running = False

# -------------------------------
# File Selection & Clear Functions
# -------------------------------
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

def clear_files():
    """Clear the list of uploaded files."""
    file_list.delete(0, tk.END)

# -------------------------------
# Show Encoding Details (Using ffprobe)
# -------------------------------
def show_encoding_details():
    """
    Open a popup that lets the user choose one of the uploaded files and then
    displays its encoding details (using ffprobe).
    """
    if file_list.get(0, tk.END) == ():
        messagebox.showinfo("No Files", "Please upload some files first.")
        return

    details_popup = ctk.CTkToplevel(root)
    details_popup.title("Select File for Encoding Details")
    details_popup.geometry("500x300")
    
    label = ctk.CTkLabel(details_popup, text="Select a file:", font=("Helvetica", 12))
    label.pack(padx=10, pady=5)
    
    # Use a standard Tkinter Listbox with dark colors.
    details_listbox = tk.Listbox(details_popup, width=60, height=6, font=("Helvetica", 10),
                                 bg="#2b2b2b", fg="white", selectbackground="#3e3e3e", selectforeground="white")
    for file in file_list.get(0, tk.END):
        details_listbox.insert(tk.END, file)
    details_listbox.pack(padx=10, pady=5)
    
    def get_details():
        selection = details_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select a file from the list.")
            return
        file_path = details_listbox.get(selection[0])
        try:
            cmd = ["ffprobe", "-v", "error", "-show_format", "-show_streams", file_path]
            details = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("ffprobe Error", f"Error retrieving details:\n{e.output}")
            return
        
        details_window = ctk.CTkToplevel(details_popup)
        details_window.title(f"Encoding Details for {os.path.basename(file_path)}")
        details_window.geometry("600x400")
        text_box = ScrolledText(details_window, wrap="word", font=("Helvetica", 10))
        text_box.pack(expand=True, fill="both")
        text_box.insert("1.0", details)
        text_box.configure(state="disabled")
    
    details_button = ctk.CTkButton(details_popup, text="Show Details", command=get_details)
    details_button.pack(padx=10, pady=10)

# -------------------------------
# Update Advanced Widgets (mp3 vs wav)
# -------------------------------
def update_format_settings(*args):
    """
    Adjust advanced settings based on the selected output format.
    For WAV:
      - Hide mp3 encoding widgets.
      - Update sample rate options to common PCM rates.
      - Show the WAV Bit Depth widget.
    For mp3:
      - Hide WAV-specific widgets.
      - Update sample rate options for compressed formats.
      - Show mp3 encoding settings (VBR/CBR).
    """
    fmt = output_format_var.get().lower()
    if fmt == "wav":
        # Hide mp3 encoding widgets.
        encoding_label.grid_forget()
        encoding_menu.grid_forget()
        vbr_quality_label.grid_forget()
        vbr_quality_menu.grid_forget()
        bitrate_label.grid_forget()
        bitrate_menu.grid_forget()
        # Update sample rate options.
        new_rates = ["44100", "48000", "96000", "192000"]
        sample_rate_var.set(new_rates[0])
        sample_rate_menu.configure(values=new_rates)
        # Show WAV Bit Depth widget.
        wav_bit_depth_label.grid(row=7, column=0, padx=10, pady=5, sticky="w")
        wav_bit_depth_menu.grid(row=7, column=1, padx=10, pady=5, sticky="ew")
    elif fmt == "mp3":
        # Hide WAV-specific widget.
        wav_bit_depth_label.grid_forget()
        wav_bit_depth_menu.grid_forget()
        new_rates = ["22050", "44100", "48000"]
        sample_rate_var.set(new_rates[0])
        sample_rate_menu.configure(values=new_rates)
        # Show mp3 encoding options.
        encoding_label.grid(row=7, column=0, padx=10, pady=5, sticky="w")
        encoding_menu.grid(row=7, column=1, padx=10, pady=5, sticky="ew")
        update_encoding_settings()

def update_encoding_settings(*args):
    """
    For mp3, based on the chosen encoding type (VBR or CBR):
      - If VBR is selected, show the VBR Quality drop-down.
      - If CBR is selected, show the Bitrate drop-down.
    """
    if output_format_var.get().lower() != "mp3":
        vbr_quality_label.grid_forget()
        vbr_quality_menu.grid_forget()
        bitrate_label.grid_forget()
        bitrate_menu.grid_forget()
        return

    if encoding_var.get() == "Variable bitrate":
        vbr_quality_label.grid(row=9, column=0, padx=10, pady=5, sticky="w")
        vbr_quality_menu.grid(row=9, column=1, padx=10, pady=5, sticky="ew")
        bitrate_label.grid_forget()
        bitrate_menu.grid_forget()
    else:
        bitrate_label.grid(row=9, column=0, padx=10, pady=5, sticky="w")
        bitrate_menu.grid(row=9, column=1, padx=10, pady=5, sticky="ew")
        vbr_quality_label.grid_forget()
        vbr_quality_menu.grid_forget()

# -------------------------------
# Animated Status Update
# -------------------------------
def animate_status():
    """Update the processing popup label with animated dots."""
    global animation_counter, animation_running
    if processing_popup is None or not animation_running:
        return
    dots = "." * (animation_counter % 4)
    status_label.configure(text=f"Converting '{current_file_name}'{dots}")
    animation_counter += 1
    processing_popup.after(500, animate_status)

# -------------------------------
# Conversion Process (Background Thread)
# -------------------------------
def conversion_process():
    """
    Convert each uploaded file using ffmpeg with the selected options.
    Runs in a background thread.
    """
    global current_file_name, animation_running
    fmt = output_format_var.get().lower()
    sample_rate = sample_rate_var.get().strip()
    channel = channel_var.get().strip()  # "Mono" or "Stereo"
    result_dir = "result"
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    for i in range(len(file_list.get(0, tk.END))):
        input_file = file_list.get(i)
        current_file_name = os.path.basename(input_file)
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(result_dir, base_name + f".{fmt}")
        command = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-ar", sample_rate
        ]
        # Set channel.
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
            continue

        command.append(output_file)
        print("Running command:", " ".join(command))
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            if processing_popup is not None:
                processing_popup.destroy()
            messagebox.showerror("Conversion Error",
                                 f"Failed to convert:\n{input_file}\nError: {e}")
            return

    animation_running = False
    if processing_popup is not None:
        processing_popup.destroy()
    messagebox.showinfo("Done", "All files have been successfully converted.")

def start_conversion():
    """
    Start the conversion process in a background thread and display a processing popup.
    """
    global processing_popup, animation_running, current_file_name, animation_counter, status_label
    processing_popup = ctk.CTkToplevel(root)
    processing_popup.title("Processing")
    status_label = ctk.CTkLabel(processing_popup, text="Preparing...", font=("Helvetica", 14))
    status_label.pack(padx=20, pady=20)
    processing_popup.geometry(f"+{root.winfo_rootx()+50}+{root.winfo_rooty()+50}")
    root.attributes("-disabled", True)

    current_file_name = ""
    animation_counter = 0
    animation_running = True
    animate_status()

    def reenable_main():
        root.attributes("-disabled", False)

    def thread_finished():
        reenable_main()

    conv_thread = threading.Thread(target=lambda: [conversion_process(),
                                                     root.after(0, thread_finished)])
    conv_thread.start()

# -------------------------------
# Main GUI – Using CustomTkinter (Dark Mode)
# -------------------------------
root = ctk.CTk()
root.title("Audio Converter")
root.geometry("500x500")

# Main frame.
frame = ctk.CTkFrame(root, corner_radius=8)
frame.pack(padx=20, pady=20, fill="both", expand=True)

# Row 0: File Selection and Clear Buttons.
buttons_frame = ctk.CTkFrame(frame)
buttons_frame.grid(row=0, column=0, columnspan=2, pady=(10, 5), sticky="ew")
select_button = ctk.CTkButton(buttons_frame, text="Select Files", command=select_files)
select_button.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="ew")
clear_button = ctk.CTkButton(buttons_frame, text="Clear Files", command=clear_files)
clear_button.grid(row=0, column=1, padx=(5, 10), pady=5, sticky="ew")

# Row 1: Listbox for Uploaded Files (standard Tkinter Listbox with dark colors).
file_list = tk.Listbox(frame, width=80, height=10, font=("Helvetica", 10),
                       bg="#2b2b2b", fg="white", selectbackground="#3e3e3e", selectforeground="white")
file_list.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="nsew")

# Row 2: Encoding Details Button.
encode_details_button = ctk.CTkButton(frame, text="Encoding Details", command=show_encoding_details)
encode_details_button.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")

# Row 3: Output Format.
output_format_label = ctk.CTkLabel(frame, text="Output Format:", font=("Helvetica", 12))
output_format_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
output_format_options = ["mp3", "wav"]
output_format_var = ctk.StringVar(value=output_format_options[0])
output_format_menu = ctk.CTkOptionMenu(frame, variable=output_format_var, values=output_format_options, font=("Helvetica", 12))
output_format_menu.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
output_format_var.trace("w", update_format_settings)

# Row 4: Sample Rate.
sample_rate_label = ctk.CTkLabel(frame, text="Sample Rate (Hz):", font=("Helvetica", 12))
sample_rate_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
sample_rate_options = ["22050", "44100", "48000"]
sample_rate_var = ctk.StringVar(value=sample_rate_options[0])
sample_rate_menu = ctk.CTkOptionMenu(frame, variable=sample_rate_var, values=sample_rate_options, font=("Helvetica", 12))
sample_rate_menu.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

# Row 5: Channel.
channel_label = ctk.CTkLabel(frame, text="Channel:", font=("Helvetica", 12))
channel_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
channel_options = ["Mono", "Stereo"]
channel_var = ctk.StringVar(value="Mono")
channel_menu = ctk.CTkOptionMenu(frame, variable=channel_var, values=channel_options, font=("Helvetica", 12))
channel_menu.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

# Row 6: (Advanced Settings for WAV or mp3)
# For WAV: WAV Bit Depth.
wav_bit_depth_label = ctk.CTkLabel(frame, text="Bit Depth (WAV):", font=("Helvetica", 12))
wav_bit_depth_options = ["16", "24", "32"]
wav_bit_depth_var = ctk.StringVar(value="16")
wav_bit_depth_menu = ctk.CTkOptionMenu(frame, variable=wav_bit_depth_var, values=wav_bit_depth_options, font=("Helvetica", 12))
# For mp3: Encoding Option (VBR/CBR).
encoding_label = ctk.CTkLabel(frame, text="Encoding:", font=("Helvetica", 12))
encoding_options = ["Variable bitrate", "Constant bitrate"]
encoding_var = ctk.StringVar(value="Variable bitrate")
encoding_menu = ctk.CTkOptionMenu(frame, variable=encoding_var, values=encoding_options, font=("Helvetica", 12))
encoding_var.trace("w", update_encoding_settings)
# (These widgets are placed via update_format_settings.)

# Row 8: Advanced Encoding Details for mp3.
# For mp3 CBR: Bitrate.
bitrate_label = ctk.CTkLabel(frame, text="Bitrate (for CBR):", font=("Helvetica", 12))
bitrate_options = ["64k", "80k", "96k", "128k", "192k", "256k", "320k"]
bitrate_var = ctk.StringVar(value=bitrate_options[0])
bitrate_menu = ctk.CTkOptionMenu(frame, variable=bitrate_var, values=bitrate_options, font=("Helvetica", 12))
# For mp3 VBR: VBR Quality.
vbr_quality_label = ctk.CTkLabel(frame, text="VBR Quality (0-9):", font=("Helvetica", 12))
vbr_quality_options = [str(i) for i in range(0, 10)]
vbr_quality_var = ctk.StringVar(value="7")
vbr_quality_menu = ctk.CTkOptionMenu(frame, variable=vbr_quality_var, values=vbr_quality_options, font=("Helvetica", 12))

# Row 10: Convert Button.
convert_button = ctk.CTkButton(frame, text="Convert", command=start_conversion, font=("Helvetica", 12, "bold"))
convert_button.grid(row=10, column=0, columnspan=2, padx=10, pady=(15, 10), sticky="ew")

# Initialize widgets according to the default format.
update_format_settings()

# Configure grid expansion.
frame.columnconfigure(0, weight=1)
frame.columnconfigure(1, weight=1)
frame.rowconfigure(1, weight=1)

root.mainloop()
