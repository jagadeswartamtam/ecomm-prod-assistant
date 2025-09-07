import importlib.metadata
packages=[
    "langchain",
    "python-dotenv",
    "langchain_core",
    "streamlit"
]
for pack in packages:
    try:
        versions=importlib.metadata.version(pack)
        print(f"{pack}=={versions}")
    except importlib.metadata.PackageNotFoundError:
        print(f"{pack} (not installed)")
