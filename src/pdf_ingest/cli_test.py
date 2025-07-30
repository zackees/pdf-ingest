import logging
import sys

from pdf_ingest.cli import main

# Enable debug logging for detailed FSSpec tracking
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# sys.argv = [
#     "pdf-ingest",
#     "--rclone-config",
#     "rclone.conf",
#     "--depth",
#     "1",
#     "dst:TorrentBooks/ia1lcpdf/a",
#     "./.output",
# ]


if __name__ == "__main__":
    sys.argv.append("--rclone-config")
    sys.argv.append("rclone.conf")
    sys.argv.append("--depth")
    sys.argv.append("1")
    sys.argv.append("dst:TorrentBooks/ia1lcpdf/a")
    sys.argv.append("./.output")
    main()
