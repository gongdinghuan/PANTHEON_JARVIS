from ddgs import DDGS

ddgs = DDGS()
results = []
for result in ddgs.text('杭州天气', max_results=3):
    results.append(result)

print(f'找到 {len(results)} 条结果:')
for r in results:
    title = r.get('title', '')[:60]
    print(f"- {title}...")

