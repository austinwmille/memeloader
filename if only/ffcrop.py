import os
import subprocess

# Define input and output folders
input_folder = "./"
output_folder = "./cropped"

os.makedirs(output_folder, exist_ok=True)

# Iterate through videos in the input folder
for filename in os.listdir(input_folder):
    if filename.endswith((".mp4", ".mkv", ".avi", ".mov")):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, f"cropped_{filename}")

        # Run cropdetect and capture the output to determine crop values
        cropdetect_command = [
            "ffmpeg", "-i", input_path,
            "-vf", "cropdetect=24:16:0",
            "-f", "null", "-"
        ]
        result = subprocess.run(cropdetect_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        crop_values = None

        # Parse crop values from output
        for line in result.stderr.splitlines():
            if "crop=" in line:
                crop_values = line.split("crop=")[1].split()[0]  # Get crop dimensions

        if crop_values:
            # Apply the crop with the detected crop values
            command = [
                "ffmpeg", "-i", input_path,
                "-vf", f"crop={crop_values}",
                "-c:a", "copy",  # Copy the audio without re-encoding
                output_path
            ]
            subprocess.run(command, check=True)
            print(f"Cropped video saved as {output_path}")
        else:
            print(f"Could not detect crop values for {filename}")
