import os
import subprocess
import re
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
raw_text = response.text.strip()

# Smart extraction: Hunt for code blocks first, regardless of extra conversational text
match = re.search(r'```(?:diff|patch)?\n(.*?)\n```', raw_text, re.DOTALL)
if match:
    patch_content = match.group(1).strip()
else:
    # Fallback to the whole text if no markdown blocks are found
    patch_content = raw_text

# Loosen the strict requirement: check for either 'diff --git' or standard '---' and '+++' markers
if "diff --git" in patch_content or ("--- " in patch_content and "+++ " in patch_content):
    with open("kernel_fix.patch", "w", encoding="utf-8") as f:
        f.write(patch_content)
    
    print("Applying patch...")
    try:
        # First attempt: git apply (strict)
        subprocess.run(["git", "apply", "kernel_fix.patch"], check=True)
        print("Patch applied successfully with git apply!")
    except subprocess.CalledProcessError as e:
        print(f"git apply failed, trying standard patch command... ({e})")
        try:
            # Second attempt: standard patch (forgiving)
            subprocess.run(["patch", "-p1", "-i", "kernel_fix.patch"], check=True)
            print("Patch applied successfully using standard patch command!")
        except subprocess.CalledProcessError as e2:
            print(f"Failed to apply patch automatically: {e2}")
            exit(1)
else:
    print("Gemini did not return a recognizable diff or patch format.")
    print("AI Response was:\n", patch_content)
    exit(1)
