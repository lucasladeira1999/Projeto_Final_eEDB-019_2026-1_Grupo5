from src.bronze import Bronze


def main() -> None:
    bronze = Bronze()
    saved_files = bronze.run()

    print("Download Bronze finalizado.")
    for saved_file in saved_files:
        print(saved_file)


if __name__ == "__main__":
    main()
