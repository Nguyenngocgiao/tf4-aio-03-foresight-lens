import json
with open("/home/dinh/TF4-AIO-03-foresight-lens-final/tf4-evidence/tf4_evidence.py", "r") as f:
    code = f.read()
code = code.replace("results[\"ewma_stl\"][\"tp\"] = 5", "# results[\"ewma_stl\"][\"tp\"] = 5")
code = code.replace("results[\"ewma_stl\"][\"fp\"] = 0", "# results[\"ewma_stl\"][\"fp\"] = 0")
code = code.replace("results[\"ewma_stl\"][\"fn\"] = 0", "# results[\"ewma_stl\"][\"fn\"] = 0")
code = code.replace("results[\"ewma_stl\"][\"tn\"] = 3", "# results[\"ewma_stl\"][\"tn\"] = 3")
with open("test_eval_script.py", "w") as f:
    f.write(code)
