import subprocess
import shutil
from gui_utils import update_log 

def detect_media_type(device, log_text):
    try:
        # Überprüfen, ob notwendige Tools installiert sind
        if not shutil.which("cdparanoia"):
            log_message = "cdparanoia is not installed. Audio CD detection will not be available."
            print(log_message)
            update_log(log_text, log_message, level="WARNING")
        if not shutil.which("dvdbackup"):
            log_message = "dvdbackup is not installed. Video/Music DVD detection will not be available."
            print(log_message)
            update_log(log_text, log_message, level="WARNING")

        # Erste Überprüfung auf den Dateisystemtyp
        result = subprocess.run(['blkid', '-p', '-o', 'value', '-s', 'TYPE', device], 
                                capture_output=True, text=True, check=True)
        media_type = result.stdout.strip()
        
        # Debug-Ausgabe des erkannten Medientyps
        log_message = f"Detected media type from blkid: {media_type}"
        print(log_message)
        update_log(log_text, log_message)

        if media_type == "udf" or media_type == "iso9660":
            # Überprüfen auf Audio CD oder DVD
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
            return "Unknown"
    except subprocess.CalledProcessError as e:
        error_message = f"Error detecting media type: {e}"
        print(error_message)
        update_log(log_text, error_message, level="ERROR")
        return "Unknown"
    
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