import subprocess
import os
import time

def convert_pcap_to_csv(pcap_path):
    csv_path = pcap_path.replace(".pcap", "_converted.csv")
    print(f"[Process] Converting {pcap_path} to {csv_path}...")
    
    cmd = [
        "tshark", "-r", pcap_path,
        "-T", "fields",
        "-e", "frame.number",
        "-e", "frame.time_relative",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "ip.proto",
        "-e", "frame.len",
        "-e", "tcp.flags",
        "-E", "header=y",
        "-E", "separator=,",
        "-E", "quote=d"
    ]
    
    start_time = time.time()
    try:
        with open(csv_path, "w") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=True)
        
        duration = time.time() - start_time
        file_size = os.path.getsize(csv_path) / (1024 * 1024)
        print(f"[Success] Completed in {duration:.2f}s. CSV Size: {file_size:.2f} MB")
    except subprocess.CalledProcessError as e:
        print(f"[Error] Failed to convert {pcap_path}: {e}")

if __name__ == "__main__":
    pcap_files = [
        "./data/CIC-IDS2017/Tuesday-WorkingHours.pcap",
        "./data/CIC-IDS2017/Wednesday-workingHours.pcap",
        "./data/CIC-IDS2017/Thursday-WorkingHours.pcap"
    ]
    
    for pcap in pcap_files:
        if os.path.exists(pcap):
            convert_pcap_to_csv(pcap)
        else:
            print(f"[Skip] {pcap} not found.")