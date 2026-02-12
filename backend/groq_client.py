import json
from groq import Groq

class GroqService:
    def __init__(self):
        self.DEFAULT_MODEL = "llama-3.3-70b-versatile"
        self.MAX_CHARS = 12000

    def analyze_code(self, api_key, code, filename, language):
        """
        Sends code to Groq API.
        """
        if not api_key:
            return {"success": False, "error": "API Key is missing."}

        # 1. Handle Truncation
        truncated = False
        if len(code) > self.MAX_CHARS:
            code = code[:self.MAX_CHARS] + '\n... (truncated)'
            truncated = True

        # 2. Construct the Prompt SAFELY (List Method)
        # This avoids the "unterminated string" error completely.
        prompt_parts = [
            f"You are Wolf AI, an elite code analyzer. Analyze this {language} code thoroughly.",
            "",
            f"FILE: {filename}",
            f"LANGUAGE: {language}",
            "",
            "CODE:",
            f"```{language.lower()}",
            code,
            "```",
            "",
            "Find ALL issues:",
            "- Syntax errors",
            "- Logic bugs",
            "- Security vulnerabilities",
            "- Performance issues",
            "- Bad practices",
            "- Type errors",
            "- Missing error handling",
            "",
            "Respond ONLY with valid JSON in this exact format:",
            "{",
            '  "errors": [',
            '    {',
            '      "line": <number>,',
            '      "type": "Error Type",',
            '      "severity": "high/medium/low",',
            '      "description": "What is wrong",',
            '      "fix": "How to fix it"',
            '    }',
            '  ],',
            '  "fixedCode": "The complete corrected code string",',
            '  "summary": "Brief summary of issues found"',
            "}",
            "",
            "Be thorough. If no issues found, return empty errors array."
        ]
        
        # Combine the list into a single string
        prompt = "\n".join(prompt_parts)

        try:
            client = Groq(api_key=api_key)

            # 3. Make API Call
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are Wolf AI, an expert code analyzer. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.DEFAULT_MODEL,
                temperature=0.2,
                max_tokens=8000,
                response_format={"type": "json_object"}
            )

            # 4. Parse Response
            response_content = chat_completion.choices[0].message.content
            result_json = json.loads(response_content)

            return {
                "success": True,
                "errors": result_json.get("errors", []),
                "fixedCode": result_json.get("fixedCode", code),
                "summary": result_json.get("summary", "Analysis complete"),
                "truncated": truncated
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Groq API Error: {str(e)}"
            }
