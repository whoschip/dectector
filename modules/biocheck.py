import os
from groq import Groq
import json


class BioCheck:
    def __init__(self):
        self.api_key = os.getenv("GROQ_KEY")
        if not self.api_key:
            raise ValueError("GROQ_KEY environment variable not set.")
        self.client = Groq(api_key=self.api_key)

    def check(self, bio, username):
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

        try:
            response = self.client.chat.completions.create(
                model="gemma2-9b-it",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": "Analyze this bio: CC7:    Op! Pt 10 (kbo) dpao h obnl kpjr (P zluk wyvvm), wslhzl vusf hkk tl pm fvb'yl h npys, huk ohz Kpzjvyk. Alea mpyza If hzrpun mvy kpzjvyk huk dolu fvb KT tl, wslhzl zahya dpao dpao h wpj vm fvby ivviz pm fvb dhua tl av zluk ihjr, zpujl P'cl nvaalu h sva vm ayvssz. Hszv P't puav yhjl wshf, zv WSLHZL jhss tl aol U-Dvyk., username: HungTEnY3arOldAAM",
                    },
                    {
                        "role": "assistant",
                        "content": '{\n        "username": "HungTEnY3arOldAAM",\n        "label": "inappropriate",\n  "reason": "This bio is encoded in caesar cipher endcode, which is a big redflag."\n}',
                    },
                    {
                        "role": "user",
                        "content": "Analyze this bio: blue: millia19\nIm a girl  username : Yamagishi_p3",
                    },
                    {
                        "role": "assistant",
                        "content": '{\n        "username": "Yamagishi_p3",\n        "label": "needs review",\n        "reason": "Bio mentions \'blue\' which is often used as a codeword  and potentially suggestive."\n} \n',
                    },
                    {
                        "role": "user",
                        "content": "Analyze this bio: i morph in studio 💔💔🫰\n\nim a loser ;-;;; username : 15yrdwllkitty",
                    },
                    {
                        "role": "assistant",
                        "content": '{\n        "username": "15yrdwllkitty",\n        "label": "inappropriate",\n        "reason": "The username includes a minor\'s age (\'15yr\') combined with \'kitty\' & \'studio\', which can be interpreted suggestively and raises concerns."\n} \n',
                    },
                    {
                        "role": "user",
                        "content": "Analyze this bio: blue:14 :D feminine boy I don't have a studio but you can message me for 💽! I'm pretty inexperienced and I'm on phone but I'm open to trying whatever :3 Im a girl username : robloxsxgamer",
                    },
                    {
                        "role": "assistant",
                        "content": '{\n        "username": "robloxsxgamer",\n        "label": "inappropriate",\n        "reason": "Mentions \'blue\', implies studio, shares personal contact info (\'message me\'), and discusses being open to trying \'whatever\' which raises concerns about potential NSFW or exploitative interactions."\n}',
                    },
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

            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                return {
                    "username": username,
                    "label": "error",
                    "reason": f"Invalid JSON from model: {e}",
                    "raw_response": content,
                }

        except Exception as e:
            return {
                "username": username,
                "label": "error",
                "reason": str(e),
            }
