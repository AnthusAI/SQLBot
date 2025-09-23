#!/usr/bin/env python3
"""
Automated test script for SQLBot textual app using pexpect.
Sends a series of messages to the textual app with timing delays.
"""

import pexpect
import sys
import time
import os
import shutil

def run_sqlbot_automation():
    """Run SQLBot and send automated messages to test the textual app."""

    # Set environment variables for the test
    env = os.environ.copy()
    env['DBT_PROFILES_DIR'] = '.dbt'
    env['DBT_PROFILE_NAME'] = 'Sakila'

    # Get current terminal size
    try:
        terminal_size = shutil.get_terminal_size()
        dimensions = (terminal_size.lines, terminal_size.columns)
    except:
        # Fallback to a reasonable size if we can't get terminal size
        dimensions = (50, 100)

    # Start the SQLBot process
    try:
        child = pexpect.spawn('sqlbot --profile Sakila', env=env, timeout=30, dimensions=dimensions)
        child.logfile_read = sys.stdout.buffer

        # Wait for the app to start up
        child.expect(pexpect.TIMEOUT, timeout=3)

        # Send first message
        message1 = "show me all the films that start with the letter A"
        child.send(message1)
        child.send('\r')

        # Wait for response
        time.sleep(5)

        # Send second message after 2 second delay
        time.sleep(2)
        message2 = "OK, so show me all the films with titles starting with B"
        child.send(message2)
        child.send('\r')

        # Wait for response
        time.sleep(5)

        # Send third message after 2 second delay
        time.sleep(2)
        message3 = "show me the top five customers by number of rentals"
        child.send(message3)
        child.send('\r')

        # Wait for final response
        time.sleep(5)

        # Keep the session alive for a bit to see final results
        time.sleep(10)

        # Send Ctrl+C to exit gracefully
        child.send('\x03')

        # Wait for process to exit
        child.expect(pexpect.EOF, timeout=5)

    except pexpect.TIMEOUT:
        child.kill(9)
    except pexpect.EOF:
        pass
    except Exception as e:
        if 'child' in locals():
            child.kill(9)

if __name__ == "__main__":
    run_sqlbot_automation()