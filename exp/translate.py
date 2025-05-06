import sys


from load_pipeline import load_model


def main() -> int:
    translator = load_model()
    print("Running the model")
    # Add your model running code here
    print("Model loaded, running translation...")
    print(translator("Bonjour tout le monde")[0]["translation_text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
