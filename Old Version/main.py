from src import amazeing_engine


if __name__ == "__main__":
    """x"""
    try:
        start_engine = amazeing_engine()
        start_engine()

    except Exception as e:
        print(f"Error in main -> {e}")
