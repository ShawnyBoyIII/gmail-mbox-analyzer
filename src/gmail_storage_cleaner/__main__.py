import sys

def main():
    # If the user passed any arguments (like a file path or flags), assume CLI
    if len(sys.argv) > 1:
        from .cli import main as cli_main
        sys.exit(cli_main())
    else:
        # Otherwise, launch the GUI
        from .gui import launch_gui
        launch_gui()

if __name__ == "__main__":
    main()
