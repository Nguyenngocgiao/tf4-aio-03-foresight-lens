import re
import os

def replace_in_file(filepath, replacement):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex to find ```mermaid ... ```
    pattern = re.compile(r'```mermaid.*?```', re.DOTALL)
    
    new_content = pattern.sub(replacement, content, count=1)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

replace_in_file(
    'docs/02_solution_design.md',
    '![Solution Design](../diagrams/02_solution_design.png)\n\n*(Sơ đồ có thể chỉnh sửa: [02_solution_design.drawio](../diagrams/02_solution_design.drawio))*'
)

replace_in_file(
    'docs/03_ai_engine_spec.md',
    '![Closed-loop Safety Pattern](../diagrams/03_ai_action_loop.png)\n\n*(Sơ đồ có thể chỉnh sửa: [03_ai_action_loop.drawio](../diagrams/03_ai_action_loop.drawio))*'
)

replace_in_file(
    'contracts/deployment-contract.md',
    '![Deployment Topology](../diagrams/deployment_topology.png)\n\n*(Sơ đồ có thể chỉnh sửa: [deployment_topology.drawio](../diagrams/deployment_topology.drawio))*'
)
print("Replaced mermaid blocks.")
