import sys

from transformers import pipeline

MODEL = "facebook/nllb-200-distilled-600M"
SOURCE_LANG = "fra_Latn"
TARGET_LANG = "eng_Latn"


def load_pipeline() -> pipeline:
    print(f"Loading model {MODEL}...")
    # Load the model and tokenizer
    # This will download the model if not already downloaded
    # return pipeline("translation", model=model, tokenizer=model, src_lang="fra_Latn", tgt_lang="eng_Latn")
    return pipeline(
        "translation",
        model=MODEL,
        tokenizer=MODEL,
        src_lang=SOURCE_LANG,
        tgt_lang=TARGET_LANG,
    )


def main() -> int:
    _ = load_pipeline()
    return 0


if __name__ == "__main__":
    sys.exit(main())
