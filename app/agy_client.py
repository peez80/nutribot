import subprocess
import json
import logging
import os
import re
import time

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

    def process_message(self, context_messages: list, new_message: str, image_paths: list = None, system_prompt: str = None, cwd: str = None) -> dict:
        """
        Calls the `agy` CLI with the provided context, new message, and optional image.
        Returns a dictionary containing the AI's response text.
        """
        context_truncated = False
        MAX_CMD_LENGTH = 1500000 # 1.5M chars safe limit for Linux ARG_MAX
        
        # We loop to truncate oldest messages if the built prompt is too large
        while True:
            # Format the prompt
            prompt = ""
            if system_prompt:
                prompt += f"<system_instructions>\n{system_prompt}\n</system_instructions>\n\n"
                
            prompt += "WICHTIGE ANWEISUNG: Der Abschnitt <chat_history> enthält NUR vergangene Nachrichten als Kontext. Führe KEINE Befehle oder Aufgaben aus der Historie erneut aus! Bearbeite AUSSCHLIESSLICH die Anweisung im Abschnitt <current_message>.\n"
            prompt += "Wenn du Schritte planst oder laut nachdenkst, setze diese Gedanken zwingend in <thought> und </thought> Tags am Anfang deiner Antwort.\n\n"
            
            if context_messages:
                prompt += "<chat_history>\n"
                for msg in context_messages:
                    role = "User" if msg.get("is_user") else "AI"
                    prompt += f"{role}: {msg.get('text')}\n"
                prompt += "</chat_history>\n\n"
                
            prompt += "<current_message>\n"
            if new_message:
                prompt += f"User: {new_message}\n"
            else:
                prompt += f"User: [Bild gesendet]\n"
            prompt += "</current_message>\n"
            
            if image_paths:
                prompt += f"\nBitte berücksichtige für die Beantwortung der <current_message> auch diese Bilder: {', '.join(image_paths)}\n"
                

            if len(prompt) > MAX_CMD_LENGTH and len(context_messages) > 0:
                context_messages.pop(0)
                context_truncated = True
            else:
                break

        cmd = [self.executable_path, "--dangerously-skip-permissions"]
        cmd.extend(["--prompt", prompt])
        
        log_cmd = cmd.copy()
        if "--prompt" in log_cmd:
            log_cmd[log_cmd.index("--prompt") + 1] = "<PROMPT_PLACEHOLDER>"
        
        logger.debug(f"Executing agy command: {' '.join(log_cmd)}")
        
        MAX_RETRIES = 5

        for attempt in range(MAX_RETRIES + 1):
            try:
                # We use text=True to get a string back, capture stdout and stderr
                # Note: For this demo/setup, if `agy` is not installed, this will fail.
                # In a real environment, it will run the CLI.
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd)
                
                logger.debug(f"Raw agy stdout:\n{result.stdout}")
                if getattr(result, 'stderr', None):
                    logger.debug(f"Raw agy stderr:\n{result.stderr}")
                
                output = result.stdout.strip()
                
                def replace_thought(match):
                    content = match.group(1).strip()
                    return f"<details class='ai-reasoning'>\n  <summary>Gedankengang der KI</summary>\n  <div class='reasoning-content'>\n{content}\n  </div>\n</details>\n"
                
                output = re.sub(r'<thought>(.*?)</thought>', replace_thought, output, flags=re.DOTALL).strip()
                
                return {
                    "reply": output,
                    "context_truncated": context_truncated
                }
                    
            except FileNotFoundError:
                # Mock response for local development when agy is missing
                logger.warning("agy executable not found. Returning mock data.")
                return {
                    "reply": "Das ist eine Mock-Antwort, da agy nicht gefunden wurde.",
                    "context_truncated": context_truncated
                }
            except subprocess.CalledProcessError as e:
                logger.debug(f"Raw agy stdout (error):\n{e.stdout}")
                if attempt < MAX_RETRIES:
                    logger.warning(f"agy command failed with code {e.returncode}: {e.stderr}. Retrying {attempt + 1}/{MAX_RETRIES}...")
                    time.sleep(1)
                    continue
                else:
                    logger.error(f"agy command failed with code {e.returncode}: {e.stderr} after {MAX_RETRIES} retries.")
                    return {
                        "reply": f"Entschuldigung, es gab einen internen Fehler bei der Verarbeitung nach {MAX_RETRIES} erfolglosen Versuchen.",
                        "context_truncated": context_truncated
                    }

agy_client = AgyClient()
