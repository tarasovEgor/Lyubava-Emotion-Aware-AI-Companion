import argparse
import os

import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Lyubava Emotion API.")

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the API server to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the API server to.",
    )
    parser.add_argument(
        "--model-dir",
        default="models/emotion_classifier",
        help="Path to trained emotion classifier model.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for local development.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    os.environ["MODEL_DIR"] = args.model_dir

    uvicorn.run(
        "lyubava.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
