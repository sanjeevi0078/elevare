import importlib

modules = [
    "models.idea_model",
    "api.validation",
]

for m in modules:
    try:
        importlib.import_module(m)
        print(f"{m}: OK")
    except Exception as e:
        # Print a short repr to avoid huge tracebacks in the terminal
        print(f"{m}: ERROR: {repr(e)}")
