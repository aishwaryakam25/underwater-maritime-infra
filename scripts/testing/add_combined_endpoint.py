file_path = r"backend\sonar_routes.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Read the endpoint code
with open('combined_analysis_endpoint.py', 'r', encoding='utf-8') as f:
    endpoint_code = f.read()

# Extract just the endpoint function (skip the docstring at top and helper)
lines = endpoint_code.split('\n')
start_idx = next(i for i, line in enumerate(lines) if '@router.post("/analyze-combined")' in line)
end_idx = next(i for i, line in enumerate(lines[start_idx:], start_idx) if line.startswith('# Helper')) - 1
endpoint_func = '\n'.join(lines[start_idx:end_idx])

# Add before the last line of the file
if '@router.post("/analyze-combined")' not in content:
    # Add at the end before any trailing whitespace
    content = content.rstrip() + '\n\n\n' + endpoint_func + '\n'
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Added combined analysis endpoint to sonar_routes.py")
else:
    print("⚠ Endpoint already exists")

input("Press Enter...")
