import subprocess
import shutil
from gui_utils import update_log

warned_dvdbackup = False

def detect_media_type(device, log_text):
    global warned_dvdbackup
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if not shutil.which("cdparanoia"):
                log_message = "cdparanoia is not installed. Audio CD detection will not be available."
                print(log_message)
                update_log(log_text, log_message, level="WARNING")
            
            if not shutil.which("dvdbackup") and not warned_dvdbackup:
                log_message = "dvdbackup is not installed. Video/Music DVD detection will not be available."
                print(log_message)
                update_log(log_text, log_message, level="WARNING")
                warned_dvdbackup = True

            # Attempt blkid detection
            result = subprocess.run(['blkid', '-p', '-o', 'value', '-s', 'TYPE', device],
                                    capture_output=True, text=True, check=False)
            if result.returncode != 0 or not result.stdout.strip():
                log_message = f"Attempt {attempt + 1}/{max_retries}: blkid failed or returned empty result. Retrying..."
                print(log_message)
                update_log(log_text, log_message, level="ERROR")
                continue

            media_type = result.stdout.strip()
            log_message = f"Detected media type from blkid: {media_type}"
            print(log_message)
            update_log(log_text, log_message)

            # If blkid fails or returns unknown, use alternative methods
            if media_type not in ["udf", "iso9660"]:
                log_message = "blkid detection uncertain. Attempting alternative detection methods."
                print(log_message)
                update_log(log_text, log_message, level="WARNING")

                # Alternative method: Scan first few sectors for media type hints
                dd_output = subprocess.run(['dd', f'if={device}', 'bs=2048', 'count=16'], 
                                           capture_output=True, text=True, check=False)
                if "CD001" in dd_output.stdout:
                    log_message = "Detected as ISO9660 file system by sector scan."
                    print(log_message)
                    update_log(log_text, log_message)
                    media_type = "iso9660"
                else:
                    log_message = "Unknown media type by sector scan. Assuming Data CD/DVD."
                    print(log_message)
                    update_log(log_text, log_message)
                    media_type = "Data CD/DVD"

            if media_type == "udf" or media_type == "iso9660":
                audio_check = subprocess.run(['cdparanoia', '-d', device, '-Q'],
                                             capture_output=True, text=True)
                if "audio tracks" in audio_check.stderr:
                    log_message = "Detected media as Audio CD"
                    print(log_message)
                    update_log(log_text, log_message)
                    return "Audio CD"
                else:
                    video_check = subprocess.run(['dvdbackup', '--info', '-i', device],
                                                 capture_output=True, text=True)
                    if "DVD-Video information" in video_check.stdout:
                        log_message = "Detected media as Video/Music DVD"
                        print(log_message)
                        update_log(log_text, log_message)
                        return "Video/Music DVD"
                    else:
                        log_message = "Detected media as Data CD/DVD"
                        print(log_message)
                        update_log(log_text, log_message)
                        return "Data CD/DVD"
            else:
                log_message = "Media type is unknown or unsupported"
                print(log_message)
                update_log(log_text, log_message, level="ERROR")
                return "Data CD/DVD"  
        except subprocess.CalledProcessError as e:
            error_message = f"Error detecting media type: {e}. Retrying..."
            print(error_message)
            update_log(log_text, error_message, level="ERROR")
            continue
        except Exception as e:
            error_message = f"Unexpected error during media detection: {e}. Retrying..."
            print(error_message)
            update_log(log_text, error_message, level="ERROR")
            continue

    final_message = "Max retries reached. Assuming media is Data CD/DVD."
    print(final_message)
    update_log(log_text, final_message, level="WARNING")
    return "Data CD/DVD"
    
def prepare_command(media_type, dvd_device, output_path, n_option, r3_option, b_option, d_option, c_option):
    if media_type == "Data CD/DVD":
        return prepare_data_cd_dvd_command(dvd_device, output_path, n_option, r3_option, b_option, d_option, c_option)
    elif media_type == "Audio CD":
        return prepare_audio_cd_command(dvd_device, output_path)
    elif media_type == "Video/Music DVD":
        return prepare_video_music_dvd_command(dvd_device, output_path)
    else:
        return None

def prepare_data_cd_dvd_command(dvd_device, output_path, n_option, r3_option, b_option, d_option, c_option):
    ddrescue_options = ['--force']
    if n_option:
        ddrescue_options.append("-n")
    if r3_option:
        ddrescue_options.append("-r3")
    if b_option:
        ddrescue_options.append("-b 2048")
    if d_option:
        ddrescue_options.append("-d")
    if c_option:
        ddrescue_options.append("-C")
    
    mapfile = f"{output_path}.map"
    return f"sudo ddrescue {' '.join(ddrescue_options)} {dvd_device} {output_path} {mapfile}"

def prepare_audio_cd_command(dvd_device, output_path):
    if shutil.which("cdparanoia") is None:
        raise RuntimeError("cdparanoia is not installed")
    return f"cdparanoia -B -d {dvd_device} -D 0 -Z {output_path}/track"

def prepare_video_music_dvd_command(dvd_device, output_path):
    if shutil.which("dvdbackup") is None:
        raise RuntimeError("dvdbackup is not installed")
    return f"dvdbackup -i {dvd_device} -o {output_path} -M"