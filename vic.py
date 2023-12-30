import os
import sys
import time
from termcolor import colored
import concurrent.futures
import requests
from ipaddress import IPv4Network, IPv4Address

# Function to send an HTTP request and process the response headers
def check_http_response(ip, timeout, output_file):
    url = f"https://{ip}"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            server_header = response.headers.get('server', '')
            if server_header:
                print(colored(f"{ip} is alive", "green"))
                print(colored(f"Server: {server_header}", "green"))
                with open(output_file, "a") as f:
                    f.write(ip + "\n")
            else:
                print(colored(f"{ip} is alive, but server header not found", "yellow"))
        else:
            print(colored(f"{ip} returned status code: {response.status_code}", "yellow"))
    except requests.exceptions.RequestException as e:
        print(colored(f"{ip} error: {str(e)}", "red"))

# Generator function to yield chunks of IP addresses from a list
def chunk_ip_addresses(ip_addresses, chunk_size):
    for i in range(0, len(ip_addresses), chunk_size):
        yield ip_addresses[i:i+chunk_size]

# Modify the process_ip function to use check_http_response
def process_ip(ip, timeout, output_file):
    check_http_response(ip, timeout, output_file)

# Function to validate and generate IP addresses within a given range
def generate_ip_addresses(start_ip, end_ip):
    start = int(IPv4Address(start_ip))
    end = int(IPv4Address(end_ip))
    ip_addresses = [str(IPv4Address(ip)) for ip in range(start, end + 1)]
    return ip_addresses

# Function to read IP addresses from a file
def read_ip_addresses_from_file(filename):
    ip_addresses = []
    with open(filename, "r") as f:
        for line in f:
            ip = line.strip()
            if ip:
                ip_addresses.append(ip)
    return ip_addresses

# Main function
def main(max_workers=None, timeout=None, output_file=None):
    input_ranges = input("Enter the CIDR ranges, IP address ranges, filename containing ip addresses, or filename containing such inputs (<filename) separated by commas: ").split(",")

    if max_workers is None:
        max_workers = (input("Enter the number of threads (the greater the number the faster). Maximum number: 48: "))

    if timeout is None:
        timeout = int(input("Enter the timeout period (in seconds): "))

    if output_file is None:
        output_file = input("Enter the name of the file to save the results: ")

    chunk_size = 12800

    # Process special input to import additional inputs from a file
    special_input = [input_range for input_range in input_ranges if input_range.startswith("<")]
    additional_inputs = []
    if special_input:
        filename = special_input[0][1:].strip()
        if os.path.isfile(filename):
            additional_inputs = read_ip_addresses_from_file(filename)
        else:
            print(colored(f"Invalid file: {filename}", "red"))
            return

    # Remove special input from the list of input_ranges
    input_ranges = [input_range for input_range in input_ranges if not input_range.startswith("<")]

    # Combine additional inputs with input_ranges
    input_ranges.extend(additional_inputs)

    start_time = time.time()

    invalid_inputs = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for input_range in input_ranges:
            range_type = None
            if "/" in input_range:
                range_type = "CIDR"
                try:
                    network = IPv4Network(input_range.strip())
                except ValueError as e:
                    invalid_inputs.append(input_range)
                    print(colored(str(e), "red"))
                    continue

                ip_addresses = [str(ip) for ip in network.hosts()]
            elif "-" in input_range:
                range_type = "IP"
                try:
                    start_ip, end_ip = input_range.strip().split("-")
                    ip_addresses = generate_ip_addresses(start_ip, end_ip)
                except (ValueError, IPv4AddressError) as e:
                    invalid_inputs.append(input_range)
                    print(colored(str(e), "red"))
                    continue
            else:
                range_type = "File"
                if not os.path.isfile(input_range):
                    invalid_inputs.append(input_range)
                    print(colored(f"Invalid file: {input_range}", "red"))
                    continue

                ip_addresses = read_ip_addresses_from_file(input_range)

            for chunk in chunk_ip_addresses(ip_addresses, chunk_size):
                futures = [executor.submit(process_ip, ip, timeout, output_file) for ip in chunk]
                for future in concurrent.futures.as_completed(futures):
                    pass

            print(colored(f"Finished processing {range_type} range: {input_range}", "cyan"))

    end_time = time.time()
    total_time = round(end_time - start_time, 2)
    print(colored("\nCOMPLETED", "green", attrs=["bold", "blink"]))
    print(colored(f"Total time taken: {total_time} seconds / {total_time/60} minutes", "green", attrs=["bold"]))

    if invalid_inputs:
        print(colored("\nERRORS IN INPUTS", "red", attrs=["bold"]))
        print(colored("The following inputs had errors and were skipped:", "red"))
        for input_range in invalid_inputs:
            print(colored(input_range, "red"))

        retry = "n" #input(colored("\nDo you want to retry with valid input ranges? (y/n): ", "red"))
        if retry.lower() == "y":
            main(max_workers, timeout, output_file)


if __name__ == "__main__":
    main()
