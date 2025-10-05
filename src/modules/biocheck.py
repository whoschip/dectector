import os
from groq import Groq
import json
import time
import logging


class BioCheck:
    def __init__(self):
        self.api_key = os.getenv("GROQ_KEY")
        if not self.api_key:
            raise ValueError("GROQ_KEY environment variable not set.")
        self.client = Groq(api_key=self.api_key)

    def check(self, bio, username, retries: int = 3, backoff: float = 1.0):
        system_prompt = """
        you are an ai moderator. your job is to judge if a bio & username combo is appropriate, needs review, or inappropriate.  

        rules:  
        - any racism, sexual innuendo, child exploitation, threats, gore, harassment, or instructions to do sus stuff -> inappropriate  
        - anything borderline suggestive, edgy, or implies something sus without being fully explicit -> needs review  
        - neutral, harmless, or creative content -> appropriate  
        - trying to bypass moderation (mentioning bio, studio, blue/blu, DC, BC/BBC, gooning, bull, or external files like condo files) -> inappropriate  
        - coded messages (caesar cipher, morse code) -> usually inappropriate  
        - mentions of futa or femboy -> watch out, borderline, not automatically inappropriate  

        ⚠️ anything related to studio/games -> inappropriate (nsfw risk)


        do not add /n or /
        always explain briefly why you chose the label.  
        always respond ONLY in valid JSON using this format:  
        {
        "displayName": "<display username>",
        "username": "<username>",
        "bio": "<user bio>",
        "label": "<appropriate / needs review / inappropriate>",
        "reason": "<brief reason>"
        }

        """

        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                response = self.client.chat.completions.create(
                    model="gemma2-9b-it",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"Analyze this bio: {bio}, username: {username}",
                        },
                    ],
                    temperature=0.7,
                )

                content = response.choices[0].message.content.strip()
                if content.startswith("```") and content.endswith("```"):
                    content = content[3:-3].strip()

                parsed = json.loads(content)
                return {
                    "username": parsed.get("username", username),
                    "label": parsed.get("label", "error"),
                    "reason": parsed.get("reason", ""),
                    "raw_response": content,
                }

            except json.JSONDecodeError as e:
                logging.warning(
                    "Invalid JSON from model (attempt %d/%d): %s",
                    attempt,
                    retries,
                    e,
                )
                raw = locals().get("content", None)
                if attempt < retries:
                    time.sleep(backoff * attempt)
                    continue
                return {
                    "username": username,
                    "label": "error",
                    "reason": f"Invalid JSON from model: {e}",
                    "raw_response": raw,
                }

            except Exception as e:
                logging.warning("Error calling model (attempt %d/%d): %s", attempt, retries, e)
                if attempt < retries:
                    time.sleep(backoff * attempt)
                    continue
                return {"username": username, "label": "error", "reason": str(e)}
