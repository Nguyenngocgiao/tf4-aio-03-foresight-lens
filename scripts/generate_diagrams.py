from drawio_builder import DrawioDiagram

STYLE_CONTAINER = "rounded=1;fillColor=#F4F8FC;strokeColor=#232F3E;strokeWidth=2;dashed=1;verticalAlign=top;align=left;fontSize=16;fontStyle=1;fontColor=#232F3E;spacingLeft=15;spacingTop=10;shadow=0;"
STYLE_BLUE = "rounded=1;fillColor=#E0F2FE;strokeColor=#0284C7;strokeWidth=2;fontSize=14;fontStyle=1;fontColor=#0284C7;shadow=1;whiteSpace=wrap;"
STYLE_ORANGE = "rounded=1;fillColor=#FFF2E8;strokeColor=#ED7100;strokeWidth=2;fontSize=14;fontStyle=1;fontColor=#ED7100;shadow=1;whiteSpace=wrap;"
STYLE_GREEN = "rounded=1;fillColor=#ECFDF5;strokeColor=#059669;strokeWidth=2;fontSize=14;fontStyle=1;fontColor=#059669;shadow=1;whiteSpace=wrap;"
STYLE_RED = "rounded=1;fillColor=#FCE4EC;strokeColor=#E7157B;strokeWidth=2;fontSize=14;fontStyle=1;fontColor=#E7157B;shadow=1;whiteSpace=wrap;"
STYLE_TEXT = "text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];autosize=1;strokeColor=none;fillColor=none;fontSize=14;fontColor=#666;fontStyle=1;"
STYLE_EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#666666;strokeWidth=2;fontColor=#333333;fontSize=12;fontStyle=1;"

def build_02_solution_design():
    d = DrawioDiagram()
    # Container
    c1 = d.add_node("AWS Cloud (Fargate + Local Compute)", 40, 40, 740, 300, STYLE_CONTAINER)
    
    # Nodes
    n1 = d.add_node("🌐 CDO Platforms\n(Payment, Fraud, Ledger)", 80, 120, 140, 80, STYLE_BLUE, parent=c1)
    n2 = d.add_node("🛡️ Pydantic\nValidation Layer", 260, 120, 140, 80, STYLE_ORANGE, parent=c1)
    n3 = d.add_node("🧮 3-Sigma Rolling\nWindow Math", 440, 120, 140, 80, STYLE_ORANGE, parent=c1)
    n4 = d.add_node("✅ Verified\nSelf-Heal Action", 620, 120, 140, 80, STYLE_GREEN, parent=c1)
    
    # Bottom nodes
    n5 = d.add_node("🔒 Context Isolation\n(X-Tenant-Id)", 350, 240, 200, 60, STYLE_RED, parent=c1)
    
    # Edges
    d.add_edge(n1, n2, "Telemetry\nSignals", STYLE_EDGE, parent=c1)
    d.add_edge(n2, n3, "Sanitized\nData", STYLE_EDGE, parent=c1)
    d.add_edge(n3, n4, "Confidence\n> 0.6", STYLE_EDGE, parent=c1)
    d.add_edge(n5, n2, "", STYLE_EDGE + "dashed=1;", parent=c1)
    d.add_edge(n5, n3, "", STYLE_EDGE + "dashed=1;", parent=c1)
    
    d.save("diagrams/02_solution_design.drawio")

def build_03_ai_action_loop():
    d = DrawioDiagram()
    # Container
    c1 = d.add_node("Closed-loop Safety Pattern", 40, 40, 740, 450, STYLE_CONTAINER)
    
    n1 = d.add_node("🚨 Anomaly\nDetected", 80, 100, 120, 60, STYLE_ORANGE, parent=c1)
    n2 = d.add_node("🎛️ Blast-Radius\nCheck", 260, 100, 120, 60, STYLE_BLUE, parent=c1)
    
    n3 = d.add_node("⚠️ Exceeds Limit", 260, 220, 120, 60, STYLE_RED, parent=c1)
    n4 = d.add_node("👨‍💻 Escalate\nto Human", 80, 220, 120, 60, "rounded=1;fillColor=#F3F4F6;strokeColor=#4B5563;strokeWidth=2;fontSize=14;fontStyle=1;shadow=1;whiteSpace=wrap;", parent=c1)
    
    n5 = d.add_node("🧪 Dry-Run Sandbox", 440, 100, 140, 60, STYLE_BLUE, parent=c1)
    n6 = d.add_node("✅ Execute Action", 620, 100, 120, 60, STYLE_GREEN, parent=c1)
    
    n7 = d.add_node("🔍 Verify Metric", 620, 220, 120, 60, STYLE_BLUE, parent=c1)
    n8 = d.add_node("⏪ Auto Rollback", 440, 220, 140, 60, STYLE_RED, parent=c1)
    n9 = d.add_node("📝 Audit Log", 620, 340, 120, 60, STYLE_GREEN, parent=c1)
    
    # Edges
    d.add_edge(n1, n2, "", STYLE_EDGE, parent=c1)
    d.add_edge(n2, n3, "Yes", STYLE_EDGE, parent=c1)
    d.add_edge(n3, n4, "", STYLE_EDGE, parent=c1)
    
    d.add_edge(n2, n5, "No", STYLE_EDGE, parent=c1)
    d.add_edge(n5, n6, "Pass", STYLE_EDGE, parent=c1)
    d.add_edge(n5, n4, "Fail", STYLE_EDGE, parent=c1)
    
    d.add_edge(n6, n7, "Wait N sec", STYLE_EDGE, parent=c1)
    d.add_edge(n7, n9, "Pass", STYLE_EDGE, parent=c1)
    d.add_edge(n7, n8, "Fail", STYLE_EDGE, parent=c1)
    
    d.save("diagrams/03_ai_action_loop.drawio")

def build_deployment_topology():
    d = DrawioDiagram()
    
    c1 = d.add_node("VPC Task Force 4", 260, 40, 500, 360, STYLE_CONTAINER)
    c2 = d.add_node("Private Subnet", 280, 100, 460, 280, STYLE_CONTAINER)
    
    n1 = d.add_node("🌐 CDO Payment", 40, 100, 160, 60, STYLE_BLUE)
    n2 = d.add_node("🌐 CDO Fraud", 40, 200, 160, 60, STYLE_BLUE)
    n3 = d.add_node("🌐 CDO Ledger", 40, 300, 160, 60, STYLE_BLUE)
    
    n4 = d.add_node("⚖️ Internal ALB", 320, 200, 140, 60, "rounded=1;fillColor=#F3E8FF;strokeColor=#9333EA;strokeWidth=2;fontSize=14;fontStyle=1;fontColor=#9333EA;shadow=1;whiteSpace=wrap;", parent=c2)
    n5 = d.add_node("🐳 ECS Fargate Task 1", 540, 140, 160, 60, STYLE_ORANGE, parent=c2)
    n6 = d.add_node("🐳 ECS Fargate Task 2", 540, 260, 160, 60, STYLE_ORANGE, parent=c2)
    
    n7 = d.add_node("🔐 Secrets Manager VPCe", 540, 40, 160, 40, STYLE_GREEN, parent=c1)
    
    d.add_edge(n1, n4, "", STYLE_EDGE)
    d.add_edge(n2, n4, "", STYLE_EDGE)
    d.add_edge(n3, n4, "", STYLE_EDGE)
    
    d.add_edge(n4, n5, "", STYLE_EDGE)
    d.add_edge(n4, n6, "", STYLE_EDGE)
    
    d.add_edge(n5, n7, "", STYLE_EDGE + "dashed=1;")
    d.add_edge(n6, n7, "", STYLE_EDGE + "dashed=1;")
    
    d.save("diagrams/deployment_topology.drawio")

build_02_solution_design()
build_03_ai_action_loop()
build_deployment_topology()
print("Generated diagrams.")
