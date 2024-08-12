#!/usr/bin/python

# A python script that parses a directory to compare two by two alphabetically
# contiguous images

# Arguments: 
# --directory : [mandatory] the directory where the files to analyze are, referred to CWD
# --pic_ext   : [optional] extension type of the pictures to analyze
# --output    : [optional] name of the CSV file to be output, default is CWD/comparison.csv
# --vmaf_exe  : [optional] fullpath to vmaf exe ; default is: $HOME/bin/vmaf

# Use argparse for argument processing

# Steps of the script:
# * get the list of the pictures, sort in alpha order, indexes are as xxx-1.png, xxx-2.png..., xxx-10.png, xxx-11.png...
# * create a temporary directory
# * call ffmpeg to convert each picture to YUV (ffmpeg options -s 1920x1080 -pix_fmt yuv422p), place YUV picture in temporary directory
# * store the yuv name in table. 
# * for each yuv file, compare yuv file with yuv (n-1) file using:
#       "vmaf -r file_n-1.yuv -d file_n.yuv --width 1920 --height 1080 --pixel_format 422 --bitdepth 8 --feature float_ssim"
#       the output is : 
#           VMAF version 17a67b2
#           1 frame  ⢀⠀ 0.00 FPS
#           vmaf_v0.6.1: 97.433662
#       Get the vmaf_v0.6.1 score
# * save into table the compared files and the comparison score
# * Export the table to csv

# Cyber-G, August 2024

import os
import argparse
import subprocess
import json
import csv
import re
from pathlib import Path

def parse_arguments():
    parser = argparse.ArgumentParser(description="Compare alphabetically contiguous images using VMAF.")
    parser.add_argument('--directory', required=True, help="The directory where the files to analyze are, referred to CWD.")
    parser.add_argument('--pic_ext', default='png', help="Extension type of the pictures to analyze, default is 'png'.")
    parser.add_argument('--output', default='comparison.csv', help="Name of the CSV file to be output, default is CWD/comparison.csv.")
    parser.add_argument('--vmaf_exe', default=str(Path.home() / 'bin' / 'vmaf'), help="Full path to vmaf executable; default is $HOME/bin/vmaf.")
    return parser.parse_args()

def get_sorted_image_list(directory, extension):
    images = sorted([f for f in os.listdir(directory) if f.endswith(f'.{extension}')], key=lambda x: int(re.findall(r'\d+', x)[-1]))
    return images

def convert_to_yuv(image_path, yuv_path):
    command = [
        'ffmpeg', '-i', image_path, '-s', '1920x1080', '-pix_fmt', 'yuv422p',
        yuv_path
    ]
    subprocess.run(command, check=True)

def compare_yuv_files(vmaf_exe, yuv_file_1, yuv_file_2, json_output_path):
    command = [
        vmaf_exe, '-r', yuv_file_1, '-d', yuv_file_2, '--width', '1920', '--height', '1080',
        '--pixel_format', '422', '--bitdepth', '8', '--json', '--output', json_output_path
    ]
    print(' '.join(command))
    subprocess.run(command, check=True)
    # for unknown reason, I did not succeed to capture the output of vmaf sent.
    # the source of vmaf conditions the print if the output is a tty or so. 
    # https://github.com/Netflix/vmaf/blob/014ea9de35d087ee714660a3ed6d8e576e23ee95/libvmaf/tools/vmaf.c#L177
    # here, the non-interactive environment may set the program not to display. 
    # to solve the issue, I export the output as JSON

    # Parse the JSON output to extract the VMAF score
    with open(json_output_path, 'r') as json_file:
        vmaf_data = json.load(json_file)
        vmaf_score = vmaf_data['frames'][0]['metrics']['vmaf']
        return vmaf_score

def main():
    args = parse_arguments()

    image_dir = Path(args.directory)
    output_csv = Path(args.output)
    pic_ext = args.pic_ext
    vmaf_exe = args.vmaf_exe

    images = get_sorted_image_list(image_dir, pic_ext)
    
    if len(images) < 2:
        print("Not enough images to compare.")
        return

    # Create a directory for YUV files
    yuv_dir = Path('yuv_dir')
    json_dir = Path('json_dir')
    yuv_dir.mkdir(exist_ok=True)
    json_dir.mkdir(exist_ok=True)

    yuv_files = []

    for image in images:
        image_path = image_dir / image
        yuv_file = Path(yuv_dir) / f"{Path(image).stem}.yuv"
        convert_to_yuv(str(image_path), str(yuv_file))
        yuv_files.append(yuv_file)

    comparison_results = []

    for i in range(1, len(yuv_files)):
        json_output_path = json_dir / f"compare_{i-1}_{i}.json"
        vmaf_score = compare_yuv_files(vmaf_exe, str(yuv_files[i-1]), str(yuv_files[i]), str(json_output_path))
        comparison_results.append({
            'Image 1': images[i-1],
            'Image 2': images[i],
            'VMAF Score': vmaf_score
        })

    with open(output_csv, mode='w', newline='') as csv_file:
        fieldnames = ['Image 1', 'Image 2', 'VMAF Score']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comparison_results)
    
    print(f"Comparison completed. Results saved to {output_csv}")

if __name__ == "__main__":
    main()
