# scripts/ai_fixer.py
import os
import subprocess
import google.generativeai as genai

# Configure Gemini API
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment.")
    exit(1)

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

# Read the build error logs captured from GitHub Actions
log_file = "build_error.log"
if os.path.exists(log_file):
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        error_logs = f.read()[-15000:]  # Grab last 15k characters of errors
else:
    error_logs = "Unknown compilation failure."

prompt = f"""
You are an expert Android kernel developer. The following kernel compilation failed on GitHub Actions.
Analyze the error logs below and provide a unified git diff patch to fix the source code.
Return ONLY the raw git diff patch format, nothing else. No markdown wrappers like ```diff.

Error Logs:
{error_logs}
"""

print("Asking Gemini for a code patch...")
response = model.generate_content(prompt)
patch_content = response.text.strip()

# Clean up potential markdown formatting if Gemini includes them anyway
if patch_content.startswith("```diff"):
    patch_content = patch_content[7:]
elif patch_content.startswith("```"):
    patch_content = patch_content[3:]
if patch_content.endswith("```"):
    patch_content = patch_content[:-3]
patch_content = patch_content.strip()

if "diff --git" in patch_content:
    with open("kernel_fix.patch", "w", encoding="utf-8") as f:
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
    print("AI Response was:\n", patch_content)
    exit(1)
