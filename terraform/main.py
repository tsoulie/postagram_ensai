import os
import subprocess


def run_script(script_name):
    result = subprocess.run(['pipenv', 'run', 'python', script_name], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running {script_name}: {result.stderr}")
    else:
        print(f"Output of {script_name}: {result.stdout}")


def main():
    # Run the main.py script
    run_script('main_server.py')

    # Run the main_serverless.py script
    run_script('main_serverless.py')


if __name__ == "__main__":
    main()
