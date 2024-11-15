import os
import subprocess

# Set the input and output folder paths
input_folder = "./"
output_folder = "./cropped"

# Make sure the output folder exists
os.makedirs(output_folder, exist_ok=True)

# Process each video in the input folder
for filename in os.listdir(input_folder):
    if filename.endswith((".mp4", ".mkv", ".avi", ".mov")):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, f"edges_{filename}")

        # Apply ffmpeg edge detection
        command = [
            "ffmpeg", "-i", input_path,
            "-vf", "edgedetect=low=0.1:high=0.4",
            "-c:a", "copy",
            output_path
        ]

        # Run the command
        subprocess.run(command, check=True)
        print(f"Edge detection applied to {filename}, saved as {output_path}")

