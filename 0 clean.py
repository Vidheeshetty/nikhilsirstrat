import subprocess

# Command to run
command = ["dot_clean", "-m", "/Volumes/T7/Code Repositories/NTbasedPlatform"]

try:
    result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("Success:\n", result.stdout)
except subprocess.CalledProcessError as e:
    print("Error:\n", e.stderr)