import sys


from load_pipeline import load_pipeline


def main() -> int:
    translator = load_pipeline()
    # Add your model running code here
    print("Model loaded, running translation...")
    print(translator("Bonjour tout le monde")[0]["translation_text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
