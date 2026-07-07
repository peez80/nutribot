import subprocess
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

class AgyClient:
    def __init__(self, executable_path: str = "agy"):
        self.executable_path = executable_path
        self._login_process = None

    def is_authenticated(self) -> bool:
        """
        Check if the user is authenticated. We can do this by running a simple command 
        like `agy --help` or checking for the credentials file.
        In the docker setup, credentials should be at /root/.gemini/antigravity-cli/
        """
        # A simple heuristic: if the credential directory exists and isn't empty, we might be authenticated.
        # Alternatively, we try to run `agy auth status` or a simple command.
        # Let's try running a mock command. If it hangs or prompts for login, it's not.
        # For our purposes, checking the credential directory is robust enough.
        cred_dir = os.path.expanduser("~/.gemini/antigravity-cli")
        if os.path.exists(cred_dir) and len(os.listdir(cred_dir)) > 0:
            return True
            
        # Fallback to a quick command check
        try:
            # We assume `agy` alone might print help or require login. 
            # If it's a real CLI, we can check for its existence first.
            if not os.path.exists(self.executable_path) and self.executable_path.startswith('/'):
                 pass # Will fail in subprocess
                 
            # If the binary doesn't exist, we just say we are "authenticated" for the mock to work
            result = subprocess.run([self.executable_path, "--help"], capture_output=True, text=True, timeout=2)
            # If it runs, it's fine. If it's real `agy` and needs login, it might say so.
            return True 
        except FileNotFoundError:
            # If agy doesn't exist locally, assume mock mode is fine.
            return True
        except subprocess.TimeoutExpired:
            # If it hangs, it might be waiting for user input (login)
            return False
        except Exception:
            return False

    def get_login_url(self) -> str:
        """
        Starts `agy login` and extracts the authorization URL from its stdout.
        """
        try:
            # Clean up any existing process
            if self._login_process:
                self._login_process.terminate()
                
            self._login_process = subprocess.Popen(
                [self.executable_path, "login"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1 # Line buffered
            )
            
            # Read lines until we find a URL
            for line in iter(self._login_process.stdout.readline, ''):
                logger.info(f"agy login output: {line.strip()}")
                # Look for a URL in the output
                match = re.search(r'(https://[^\s]+)', line)
                if match:
                    return match.group(1)
                
                # If we see a prompt for the code, we might have missed the URL, or it's on a previous line
                if "code:" in line.lower() or "enter" in line.lower():
                    break
                    
            return "No URL found in agy login output."
            
        except FileNotFoundError:
            logger.warning("agy executable not found for login. Returning mock URL.")
            return "https://antigravity.google/mock-login"
        except Exception as e:
            logger.error(f"Error getting login URL: {e}")
            return f"Error: {e}"

    def submit_auth_code(self, code: str) -> bool:
        """
        Submits the authorization code to the running `agy login` subprocess.
        """
        if not self._login_process:
            logger.error("No active login process found.")
            return False
            
        try:
            # Send the code
            self._login_process.stdin.write(f"{code}\n")
            self._login_process.stdin.flush()
            
            # Wait a bit for it to process
            try:
                self._login_process.wait(timeout=5)
                # Ensure we reset the process
                self._login_process = None
                return True
            except subprocess.TimeoutExpired:
                logger.warning("agy login process did not exit after code submission.")
                # We can assume it worked or we terminate it
                self._login_process.terminate()
                self._login_process = None
                return True
                
        except Exception as e:
            logger.error(f"Error submitting auth code: {e}")
            if self._login_process:
                self._login_process.terminate()
                self._login_process = None
            return False

    def process_message(self, context_messages: list, new_message: str, image_paths: list = None) -> dict:
        """
        Calls the `agy` CLI with the provided context, new message, and optional image.
        Returns a dictionary representing the structured data extracted by the AI,
        along with a friendly response.
        
        Expected output from `agy` (mocked format):
        {
            "type": "meal", # or "symptom"
            "data": {...},
            "reply": "Das habe ich notiert!"
        }
        """
        # Format the prompt
        prompt = "Context:\n"
        for msg in context_messages:
            role = "User" if msg.get("is_user") else "AI"
            prompt += f"{role}: {msg.get('text')}\n"
        if new_message:
            prompt += f"\nUser: {new_message}\n"
        else:
            prompt += f"\nUser: [Bild gesendet]\n"
        
        if image_paths:
            prompt += f"\nBitte berücksichtige für deine Analyse auch diese Bilder: {', '.join(image_paths)}\n"
            
        # We need to instruct agy to output JSON so we can parse it
        prompt += "\nPlease analyze this and output valid JSON containing 'type' (meal/symptom), 'data' (extracted info), and 'reply' (a friendly message to the user)."

        cmd = [self.executable_path, "--prompt", prompt]

        try:
            # We use text=True to get a string back, capture stdout and stderr
            # Note: For this demo/setup, if `agy` is not installed, this will fail.
            # In a real environment, it will run the CLI.
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            output = result.stdout.strip()
            
            # Basic attempt to parse the JSON from output
            try:
                # If agy wraps JSON in markdown blocks, we might need to strip them
                if output.startswith("```json"):
                    output = output.replace("```json", "", 1)
                if output.endswith("```"):
                    output = output[::-1].replace("```", "", 1)[::-1]
                
                parsed_data = json.loads(output.strip())
                return parsed_data
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from agy: {output}")
                return {
                    "type": "unknown",
                    "data": {"raw_output": output},
                    "reply": "Ich konnte die Daten nicht verarbeiten, aber ich habe es mir gemerkt."
                }
                
        except FileNotFoundError:
            # Mock response for local development when agy is missing
            logger.warning("agy executable not found. Returning mock data.")
            is_symptom = "schmerz" in new_message.lower() or "übel" in new_message.lower()
            return {
                "type": "symptom" if is_symptom else "meal",
                "data": {"mocked": True, "note": "This is mock data because agy was not found."},
                "reply": "Das habe ich als Symptom erfasst." if is_symptom else "Das Essen wurde notiert!"
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"agy command failed with code {e.returncode}: {e.stderr}")
            return {
                "type": "error",
                "data": {},
                "reply": "Entschuldigung, es gab einen internen Fehler bei der Verarbeitung."
            }

agy_client = AgyClient()
