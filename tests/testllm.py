from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "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"
)

completion = client.chat.completions.create(
  model="minimaxai/minimax-m2.1",
  messages=[{"role":"user","content":""}],
  temperature=1,
  top_p=0.95,
  max_tokens=8192,
  stream=True
)

for chunk in completion:
  if not getattr(chunk, "choices", None):
    continue
  if chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="")
  

