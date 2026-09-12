import os
import subprocess
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")

# Read the last build error logs (assumed saved in an artifact or captured)
log_file = "build_error.log"
if os.path.exists(log_file):
    with open(log_file, "r") as f:
        error_logs = f.read()[-10000:] # Grab last 10k characters of errors
else:
    error_logs = "Unknown compilation failure."

prompt = f"""
You are an expert Android kernel developer. The following kernel compilation failed.
Analyze the error and provide a unified git diff patch to fix the source code.
Return ONLY the raw git diff patch format, nothing else. No markdown wrappers.

Errors:
{error_logs}
"""

print("Asking Gemini for a code patch...")
response = model.generate_content(prompt)
patch_content = response.text.strip()

# Clean up potential markdown formatting from LLM response
if patch_content.startswith("```diff"):
    patch_content = patch_content[7:]
if patch_content.endswith("```"):
    patch_content = patch_content[:-3]

if "diff --git" in patch_content:
    with open("kernel_fix.patch", "w") as f:
        f.write(patch_content)
    
    print("Applying patch...")
    try:
        subprocess.run(["git", "apply", "kernel_fix.patch"], check=True)
        print("Patch applied successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Failed to apply patch automatically: {e}")
        exit(1)
else:
    print("Gemini did not return a valid diff format.")
    exit(1)
